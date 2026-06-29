# Ensure Windows Proactor event loop is used so subprocesses (Playwright) can run
# Ensure Windows Proactor event loop is used so subprocesses (Playwright) can run
"""
crawler.py — Production-grade async API documentation crawler.

Architecture:
    asyncio.Queue  →  N worker coroutines  →  two-tier fetch (httpx → Playwright)

Workers pull (url, depth) tuples from a shared queue, fetch the page using
the fast httpx tier first and falling back to Playwright only for JS-heavy
pages, then push newly-discovered links back into the queue.

No recursive task spawning. No ensure_future(). No all_tasks() polling.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import sys
import time
import urllib.parse
from typing import Any, Dict, List, Optional, Set

import httpx
from bs4 import BeautifulSoup

# ── Windows ProactorEventLoop (required for Playwright sub-processes) ─────────
if sys.platform == "win32":
    try:
        if not isinstance(
            asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy
        ):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

logger = logging.getLogger("smart_devtool.crawler")

# ── Constants ─────────────────────────────────────────────────────────────────

# If the stripped visible text from an httpx response is shorter than this
# the page is almost certainly a JS shell → fall back to Playwright.
_MIN_VISIBLE_CHARS: int = 500

# File extensions that are never useful to crawl.
_SKIP_EXTENSIONS: tuple[str, ...] = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",
    ".pdf", ".css", ".js", ".json", ".xml",
    ".zip", ".tar", ".gz", ".tar.gz",
    ".mp3", ".mp4", ".wav", ".ogg",
    ".woff", ".woff2", ".ttf", ".eot",
)

# URL path prefixes / substrings that are rarely useful for API reference docs.
_IGNORED_PATH_PATTERNS: tuple[str, ...] = (
    "/guides/", "/learn/", "/blog/", "/community/",
    "/examples/", "/cookbook/", "/workspace/", "/ads/",
    "/azure/", "/enterprise/", "/pricing/", "/showcase/",
    "/changelog/", "/status/", "/legal/", "/privacy/",
)

# Strings whose presence in a page (HTML or error message) indicates anti-bot.
_ANTIBOT_MARKERS: tuple[str, ...] = (
    "blocked by anti-bot", "cloudflare", "ddos protection",
    "captcha", "security challenge", "enable javascript",
    "anti-bot protection", "blocked by cloudflare", "access denied",
    "checking your browser", "perimeterx", "akamai", "datadome",
)

# HTTP status codes that should be retried.
_TRANSIENT_STATUSES: frozenset[int] = frozenset({500, 502, 503, 504})

# HTTP status codes that are permanent failures — never retry.
_PERMANENT_FAIL_STATUSES: frozenset[int] = frozenset({403, 404, 410})

# Fake browser headers sent with every httpx request.
_BROWSER_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


# ── Result type alias ─────────────────────────────────────────────────────────

CrawlItem = Dict[str, Any]


# ── Internal data class ───────────────────────────────────────────────────────

class _CrawlTask:
    """Lightweight value object placed on the asyncio.Queue."""

    __slots__ = ("url", "depth")

    def __init__(self, url: str, depth: int) -> None:
        self.url = url
        self.depth = depth


# ── Main class ────────────────────────────────────────────────────────────────

class APIDocCrawler:
    """
    Production-grade async crawler for API documentation sites.

    Public interface (unchanged — drop-in replacement):

        crawler = APIDocCrawler(max_depth=2)
        results = await crawler.crawl("https://example.com/docs/api")

    Parameters
    ----------
    max_depth:
        How many link-hops to follow from the root URL (0 = root page only).
    delay_ms:
        Polite delay (milliseconds) each worker sleeps *after* completing a page.
    http_workers:
        Maximum number of concurrent httpx fetches.
    browser_workers:
        Maximum number of concurrent Playwright browser pages.
        A single browser instance is reused for all pages.
    """

    def __init__(
        self,
        max_depth: int = 2,
        delay_ms: int = 100,
        http_workers: int = 30,
        browser_workers: int = 5,
        # Legacy alias kept for callers that passed max_concurrent= before.
        max_concurrent: Optional[int] = None,
        max_browser_concurrent: Optional[int] = None,
    ) -> None:
        self.max_depth = max_depth
        self.delay_ms = delay_ms
        self.http_workers = max_concurrent if max_concurrent is not None else http_workers
        self.browser_workers = (
            max_browser_concurrent if max_browser_concurrent is not None else browser_workers
        )

    # ── Public entry point ────────────────────────────────────────────────────

    async def crawl(self, root_url: str) -> List[CrawlItem]:
        """
        Crawl *root_url* and all reachable pages within its domain up to
        *max_depth* link-hops deep.

        Returns a list of dicts conforming to the project result schema.
        """
        # On Windows, Playwright requires a ProactorEventLoop.  If we are
        # already running inside a non-Proactor loop (e.g. a FastAPI test
        # runner using SelectorEventLoop), dispatch to a dedicated thread.
        if sys.platform == "win32":
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop is not None and not isinstance(loop, asyncio.ProactorEventLoop):
                logger.info(
                    "Non-ProactorEventLoop detected on Windows. "
                    "Dispatching crawler to a ProactorEventLoop thread."
                )
                return await self._run_in_proactor_thread(root_url)

        return await self._run(root_url)

    # ── Windows thread shim ───────────────────────────────────────────────────

    async def _run_in_proactor_thread(self, root_url: str) -> List[CrawlItem]:
        """Run _run() inside a new thread that owns a ProactorEventLoop."""
        import threading

        caller_loop = asyncio.get_running_loop()
        future: asyncio.Future[List[CrawlItem]] = caller_loop.create_future()

        def _thread() -> None:
            if sys.platform == "win32":
                try:
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                except Exception:
                    pass
            inner_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(inner_loop)
            try:
                result = inner_loop.run_until_complete(self._run(root_url))
                caller_loop.call_soon_threadsafe(future.set_result, result)
            except Exception as exc:
                caller_loop.call_soon_threadsafe(future.set_exception, exc)
            finally:
                inner_loop.close()

        thread = threading.Thread(target=_thread, name="ProactorCrawlerThread", daemon=True)
        thread.start()
        return await future

    # ── Core engine ───────────────────────────────────────────────────────────

    async def _run(self, root_url: str) -> List[CrawlItem]:
        """
        Main crawl engine.

        1. Validate the root URL and derive the allowed domain + root path.
        2. Build shared state (queue, visited set, result list, semaphores).
        3. Create one shared httpx.AsyncClient (connection-pooled, keep-alive).
        4. Create one Crawl4AI AsyncWebCrawler (single browser instance).
        5. Spawn N worker coroutines that drain the queue.
        6. Wait for the queue to be fully processed, then cancel workers.
        7. Return the collected results.
        """
        # Ensure ProactorEventLoop on Windows (also called from _run_in_proactor_thread).
        if sys.platform == "win32":
            try:
                if not isinstance(
                    asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy
                ):
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception:
                pass

        # ── Validate root URL ─────────────────────────────────────────────────
        parsed_root = urllib.parse.urlparse(root_url)
        allowed_domain: str = parsed_root.netloc
        if not allowed_domain:
            raise ValueError(f"APIDocCrawler: invalid root URL '{root_url}'")
        root_path: str = parsed_root.path.rstrip("/").lower() or "/"

        logger.info("Crawler starting: root=%s depth=%d", root_url, self.max_depth)
        print(f"\n[CRAWLER] Starting -> {root_url}  (max_depth={self.max_depth})\n")
        t0 = time.perf_counter()

        # ── Shared state ──────────────────────────────────────────────────────
        queue: asyncio.Queue[_CrawlTask] = asyncio.Queue()
        visited: Set[str] = set()
        results: List[CrawlItem] = []
        counters: Dict[str, int] = {"ok": 0, "skip": 0, "fail": 0, "http": 0, "browser": 0}
        page_index: int = 0
        state_lock = asyncio.Lock()

        # Seed the queue with the root URL.
        normalised_root = _normalise_url(root_url)
        visited.add(normalised_root)
        await queue.put(_CrawlTask(normalised_root, 0))

        # ── Semaphores ────────────────────────────────────────────────────────
        http_sem = asyncio.Semaphore(self.http_workers)
        browser_sem = asyncio.Semaphore(self.browser_workers)

        # ── Crawl4AI / Playwright setup ───────────────────────────────────────
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

        browser_cfg = BrowserConfig(
            headless=True,
            verbose=False,
            light_mode=True,
            memory_saving_mode=True,
            avoid_ads=True,
        )
        run_cfg = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            stream=False,
            exclude_all_images=True,
            wait_for_images=False,
            page_timeout=30_000,       # 30 s — Spotify pages genuinely need it
            delay_before_return_html=0.5,
        )

        # ── httpx client (shared, pooled, keep-alive) ─────────────────────────
        httpx_client = httpx.AsyncClient(
            headers=_BROWSER_HEADERS,
            timeout=httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0),
            follow_redirects=True,
            limits=httpx.Limits(
                max_connections=self.http_workers + 10,
                max_keepalive_connections=self.http_workers,
                keepalive_expiry=30.0,
            ),
            http2=False,  # Some doc sites misbehave with HTTP/2; keep HTTP/1.1
        )

        # ── Worker coroutine ──────────────────────────────────────────────────
        async def worker(worker_id: int, pw_crawler: AsyncWebCrawler) -> None:
            """
            Continuously takes tasks from the queue, fetches and processes each
            page, and enqueues newly-discovered links.  Exits when cancelled.
            """
            nonlocal page_index

            while True:
                task: _CrawlTask = await queue.get()
                try:
                    async with state_lock:
                        page_index += 1
                        idx = page_index
                    print(f"[{idx}] Crawling -> {task.url}\n")

                    result = await _fetch_page(
                        url=task.url,
                        depth=task.depth,
                        allowed_domain=allowed_domain,
                        httpx_client=httpx_client,
                        pw_crawler=pw_crawler,
                        run_cfg=run_cfg,
                        http_sem=http_sem,
                        browser_sem=browser_sem,
                    )

                    # ── Record outcome ────────────────────────────────────────
                    async with state_lock:
                        if result["status"] == "success":
                            counters["ok"] += 1
                            counters["http" if result.get("tier") == "http" else "browser"] += 1
                            results.append(result["item"])

                            # Enqueue discovered child links.
                            if task.depth < self.max_depth:
                                for link in result.get("links", []):
                                    if _should_crawl(link, allowed_domain, root_path) and link not in visited:
                                        visited.add(link)
                                        await queue.put(_CrawlTask(link, task.depth + 1))

                        elif result["status"] == "skipped":
                            counters["skip"] += 1
                        else:
                            counters["fail"] += 1
                            logger.warning("FAILED %s — %s", task.url, result.get("error"))

                except Exception as exc:
                    logger.exception("Worker %d unhandled error on %s: %s", worker_id, task.url, exc)
                    async with state_lock:
                        counters["fail"] += 1
                finally:
                    queue.task_done()
                    await asyncio.sleep(self.delay_ms / 1000.0)

        # ── Launch workers inside a single browser context ────────────────────
        async with AsyncWebCrawler(config=browser_cfg) as pw_crawler:
            workers = [
                asyncio.create_task(worker(i, pw_crawler), name=f"crawler-worker-{i}")
                for i in range(max(self.http_workers, 1))
            ]

            # Block until every queued task has been processed.
            await queue.join()

            # Workers are now idle and waiting on queue.get() — cancel them.
            for w in workers:
                w.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

        await httpx_client.aclose()

        # ── Summary ───────────────────────────────────────────────────────────
        elapsed = time.perf_counter() - t0
        total_fetched = counters["ok"]
        print(
            "\n===================================\n"
            "Crawler Summary\n"
            f"Pages Crawled   : {counters['ok']}\n"
            f"  ↳ httpx (fast): {counters['http']}/{total_fetched}\n"
            f"  ↳ Browser fall: {counters['browser']}/{total_fetched}\n"
            f"Pages Skipped   : {counters['skip']}\n"
            f"Pages Failed    : {counters['fail']}\n"
            "===================================\n"
            f"Completed  Time: {elapsed:.1f}s\n"
        )
        logger.info(
            "Crawl complete in %.1fs — ok=%d skip=%d fail=%d",
            elapsed, counters["ok"], counters["skip"], counters["fail"],
        )
        return results


# ── Two-tier page fetcher (module-level, pure function) ───────────────────────

async def _fetch_page(
    *,
    url: str,
    depth: int,
    allowed_domain: str,
    httpx_client: httpx.AsyncClient,
    pw_crawler: Any,                  # crawl4ai.AsyncWebCrawler
    run_cfg: Any,                     # crawl4ai.CrawlerRunConfig
    http_sem: asyncio.Semaphore,
    browser_sem: asyncio.Semaphore,
) -> Dict[str, Any]:
    """
    Attempt to fetch *url* in two tiers:

    Tier 1 — httpx (fast, ~0.3-1 s):
        Performs a plain HTTP GET.  If the response contains enough visible
        text (≥ _MIN_VISIBLE_CHARS) it is returned immediately.

    Tier 2 — Playwright via Crawl4AI (~15-30 s):
        Used only when Tier 1 returns a JS-shell page or fails transiently.
        Guarded by *browser_sem* to cap concurrent open browser tabs.

    Returns a dict with keys:
        status  : "success" | "skipped" | "failed"
        tier    : "http" | "browser"          (only on success)
        item    : CrawlItem                   (only on success)
        links   : List[str]                   (only on success)
        error   : str                         (only on failure)
    """
    # ── Tier 1: httpx ────────────────────────────────────────────────────────
    async with http_sem:
        http_result = await _httpx_fetch(url, depth, allowed_domain, httpx_client)

    if http_result["status"] == "success":
        return http_result

    if http_result["status"] == "skipped":
        logger.info("Trying browser fallback for %s", url)

    # Permanent HTTP failures (403, 404) → do not waste a browser slot.
    if http_result.get("permanent"):
        return http_result

    # ── Tier 2: Playwright ────────────────────────────────────────────────────
    logger.debug("Browser fallback: %s (reason: %s)", url, http_result.get("error", "js-shell"))
    print(f"[BROWSER] Fallback -> {url}\n")

    async with browser_sem:
        return await _playwright_fetch(url, depth, allowed_domain, pw_crawler, run_cfg)


# ── Tier 1: httpx fetch ───────────────────────────────────────────────────────

async def _httpx_fetch(
    url: str,
    depth: int,
    allowed_domain: str,
    client: httpx.AsyncClient,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    Fetch *url* with httpx, applying exponential-backoff retries for transient
    errors.  Returns a status dict (see _fetch_page docstring).
    """
    attempt = 0
    last_error: str = ""

    while attempt <= max_retries:
        if attempt > 0:
            backoff = min(2 ** (attempt - 1), 8)
            await asyncio.sleep(backoff)

        try:
            resp = await client.get(url)

            # ── Permanent failures ────────────────────────────────────────────
            if resp.status_code in _PERMANENT_FAIL_STATUSES:
                return {
                    "status": "failed",
                    "error": f"HTTP {resp.status_code}",
                    "permanent": True,
                }

            # ── Transient server errors → retry ──────────────────────────────
            if resp.status_code in _TRANSIENT_STATUSES:
                last_error = f"HTTP {resp.status_code}"
                attempt += 1
                continue

            # ── Non-2xx that is not in the above sets → fail immediately ──────
            if not (200 <= resp.status_code < 300):
                return {
                    "status": "failed",
                    "error": f"HTTP {resp.status_code}",
                    "permanent": False,
                }

            html: str = resp.text

            # ── Anti-bot detection ────────────────────────────────────────────
            if _is_antibot(html.lower()):
                logger.warning("Anti-bot detected for %s", url)
                return {
                    "status": "failed",
                    "error": "anti-bot (httpx)",
                    "permanent": False,
                }

            # ── Content quality check ─────────────────────────────────────────
            soup = BeautifulSoup(html, "html.parser")
            _strip_noise(soup)
            visible_text = soup.get_text(separator=" ", strip=True)

            if len(visible_text) < _MIN_VISIBLE_CHARS:
                # JS-shell page — signal to fall through to Playwright.
                return {"status": "failed", "error": "js-shell", "permanent": False}

            # ── Success ───────────────────────────────────────────────────────
            links = _extract_links(soup, url, allowed_domain)
            item = _build_item(url, html, soup, allowed_domain, depth)
            return {"status": "success", "tier": "http", "item": item, "links": links}

        except httpx.TimeoutException as exc:
            last_error = f"timeout: {exc}"
            attempt += 1
        except httpx.ConnectError as exc:
            last_error = f"connect error: {exc}"
            attempt += 1
        except httpx.RemoteProtocolError as exc:
            last_error = f"protocol error: {exc}"
            attempt += 1
        except httpx.RequestError as exc:
            # Other network-level errors — treat as transient.
            last_error = f"request error: {exc}"
            attempt += 1
        except Exception as exc:
            # Unexpected — do not retry.
            return {"status": "failed", "error": str(exc), "permanent": False}

    return {"status": "failed", "error": last_error, "permanent": False}


# ── Tier 2: Playwright fetch ──────────────────────────────────────────────────

async def _playwright_fetch(
    url: str,
    depth: int,
    allowed_domain: str,
    pw_crawler: Any,
    run_cfg: Any,
    max_retries: int = 2,
) -> Dict[str, Any]:
    """
    Fetch *url* using the Crawl4AI Playwright crawler.
    Retries only transient failures with exponential backoff.
    """
    attempt = 0
    last_error: str = ""

    while attempt <= max_retries:
        if attempt > 0:
            await asyncio.sleep(2 ** (attempt - 1))

        try:
            result = await pw_crawler.arun(url=url, config=run_cfg)

            err_lower = (result.error_message or "").lower()
            html_lower = (result.cleaned_html or result.html or "").lower()

            # ── Anti-bot detection ────────────────────────────────────────────
            if _is_antibot(err_lower) or _is_antibot(html_lower):
                return {"status": "skipped", "error": "anti-bot (browser)"}

            if result.success and (result.html or result.cleaned_html):
                html = result.cleaned_html or result.html or ""
                soup = BeautifulSoup(html, "html.parser")
                links = _extract_links(soup, url, allowed_domain)
                item = _build_item(url, html, soup, allowed_domain, depth)
                return {"status": "success", "tier": "browser", "item": item, "links": links}

            # ── Failure classification ────────────────────────────────────────
            status_code = getattr(result, "status_code", None)

            if status_code in _PERMANENT_FAIL_STATUSES or any(
                w in err_lower for w in ("404", "403", "invalid url", "not found")
            ):
                return {
                    "status": "failed",
                    "error": result.error_message or f"HTTP {status_code}",
                    "permanent": True,
                }

            is_transient = status_code in _TRANSIENT_STATUSES or any(
                w in err_lower
                for w in ("timeout", "timed out", "deadline", "network", "connection",
                           "dns", "unreachable", "refused", "reset")
            )
            if is_transient:
                last_error = result.error_message or f"transient HTTP {status_code}"
                attempt += 1
                continue

            return {
                "status": "failed",
                "error": result.error_message or "unknown browser failure",
                "permanent": False,
            }

        except Exception as exc:
            err_str = str(exc).lower()
            if _is_antibot(err_str):
                return {"status": "skipped", "error": "anti-bot (browser exception)"}
            if any(w in err_str for w in ("404", "403", "invalid url", "not found")):
                return {"status": "failed", "error": str(exc), "permanent": True}
            if any(w in err_str for w in ("timeout", "timed out", "deadline", "network",
                                           "connection", "dns", "unreachable", "refused", "reset")):
                last_error = str(exc)
                attempt += 1
            else:
                return {"status": "failed", "error": str(exc), "permanent": False}

    return {"status": "failed", "error": last_error or "max retries exceeded", "permanent": False}


# ── URL utilities ─────────────────────────────────────────────────────────────

def _normalise_url(url: str) -> str:
    """
    Normalise a URL by:
      • stripping the fragment (#section)
      • removing the query string
      • lower-casing scheme and host
      • removing trailing slashes from the path
    """
    p = urllib.parse.urlparse(url)
    normalised = urllib.parse.urlunparse((
        p.scheme.lower(),
        p.netloc.lower(),
        p.path.rstrip("/") or "/",
        "",   # params
        "",   # query  ← stripped
        "",   # fragment ← stripped
    ))
    return normalised


def _should_crawl(url: str, allowed_domain: str, root_path: str) -> bool:
    """
    Return True only if *url* is worth crawling:
      • Same domain as the root.
      • http / https scheme.
      • Not a media/asset file.
      • Not on the ignore-list of non-doc path prefixes.
      • Starts with the root path OR matches common doc sub-paths.
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    if parsed.netloc.lower() != allowed_domain.lower():
        return False

    path = parsed.path.lower()

    if any(path.endswith(ext) for ext in _SKIP_EXTENSIONS):
        return False

    if any(pat in path for pat in _IGNORED_PATH_PATTERNS):
        return False

    # Allow if the URL is within the root path subtree.
    if root_path and root_path != "/":
        if path == root_path or path.startswith(root_path + "/"):
            return True
        # Also allow well-known API doc sub-trees even outside the root path.
        common = ("/docs", "/api", "/reference", "/api-reference", "/developer")
        return any(path == c or path.startswith(c + "/") for c in common)

    return True


def _extract_links(soup: BeautifulSoup, base_url: str, allowed_domain: str) -> List[str]:
    """
    Extract, normalise, and deduplicate all anchor hrefs in *soup* that
    belong to *allowed_domain*.
    """
    seen: Set[str] = set()
    links: List[str] = []

    for tag in soup.find_all("a", href=True):
        href: str = tag["href"].strip()
        if not href or href.startswith("javascript:") or href.startswith("#"):
            continue
        try:
            absolute = urllib.parse.urljoin(base_url, href)
            normalised = _normalise_url(absolute)
            parsed = urllib.parse.urlparse(normalised)
        except Exception:
            continue

        if parsed.netloc.lower() != allowed_domain.lower():
            continue
        if parsed.scheme not in ("http", "https"):
            continue
        if any(parsed.path.lower().endswith(ext) for ext in _SKIP_EXTENSIONS):
            continue
        if normalised not in seen:
            seen.add(normalised)
            links.append(normalised)

    return links


# ── HTML helpers ──────────────────────────────────────────────────────────────

def _strip_noise(soup: BeautifulSoup) -> None:
    """Remove script, style, noscript, and SVG tags in-place."""
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()


def _get_title(soup: BeautifulSoup) -> str:
    """Extract the page <title> or return an empty string."""
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    # Fallback: first <h1>
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return ""


def _build_item(
    url: str,
    html: str,
    soup: BeautifulSoup,
    allowed_domain: str,
    depth: int,
) -> CrawlItem:
    """Assemble the result dict that downstream pipeline stages expect."""
    return {
        "url": url,
        "html": html,
        "metadata": {
            "url": url,
            "title": _get_title(soup),
            "markdown_path": f"data/crawled/{allowed_domain}/",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "depth": depth,
        },
    }


# ── Anti-bot detection ────────────────────────────────────────────────────────

def _is_antibot(text: str) -> bool:
    """Return True if *text* contains any known anti-bot marker."""
    return any(marker in text for marker in _ANTIBOT_MARKERS)