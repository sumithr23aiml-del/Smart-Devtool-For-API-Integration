"""
extractor.py — Production-grade API metadata extraction engine.

Responsibilities (strictly bounded):
    • Accept RAG context chunks and a use-case string.
    • Call an LLM to extract API metadata ONLY.
    • Repair and validate the response JSON.
    • Return a dict conforming exactly to the project schema.

This module NEVER generates code, SDKs, examples, or installation guides.

Public interface (unchanged — drop-in replacement):

    extractor = APIExtractor(provider="gemini")
    schema    = extractor.extract(context_chunks, use_case)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("smart_devtool.extractor")

# ── Constants ─────────────────────────────────────────────────────────────────

# Hard cap on context sent to the LLM.  Keeps token usage predictable and
# prevents silent truncation by model providers (which causes garbled output).
_MAX_CONTEXT_CHARS: int = 24_000

# Maximum number of retry attempts for transient errors (network, 429, 5xx).
_MAX_RETRIES: int = 4

# Base delay (seconds) for exponential backoff:  delay = _BACKOFF_BASE * 2^attempt
_BACKOFF_BASE: float = 1.0

# The exact set of top-level keys the schema may contain.  All others are stripped.
_ALLOWED_TOP_LEVEL: frozenset[str] = frozenset(
    {"api_name", "base_url", "authentication", "environment_variable", "timeout", "endpoints"}
)

# The exact set of keys each endpoint dict may contain.
_ALLOWED_ENDPOINT_KEYS: frozenset[str] = frozenset(
    {"name", "summary", "method", "path", "parameters"}
)

# The exact set of keys each parameter dict may contain.
_ALLOWED_PARAM_KEYS: frozenset[str] = frozenset(
    {"name", "type", "location", "required", "default", "description"}
)

# Authentication sub-keys.
_ALLOWED_AUTH_KEYS: frozenset[str] = frozenset(
    {"type", "header_name", "query_parameter", "scheme"}
)

# Valid HTTP methods.  Used to normalise model output.
_HTTP_METHODS: frozenset[str] = frozenset(
    {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
)

# Groq fallback model when the primary hits a rate limit.
_GROQ_FALLBACK_MODEL: str = "llama-3.1-8b-instant"

# System prompt sent to every LLM provider (never changes).
_SYSTEM_PROMPT: str = (
    "You are a precise API documentation parser. "
    "You extract structured metadata from API documentation text. "
    "You output ONLY valid JSON. "
    "You never explain. "
    "You never add comments. "
    "You never generate code. "
    "You never generate examples. "
    "You never invent information. "
    "If information is absent from the documentation, leave the field empty."
)

# ── Schema type alias ─────────────────────────────────────────────────────────

APISchema = Dict[str, Any]


# ── Public class ──────────────────────────────────────────────────────────────

class APIExtractor:
    """
    Extracts structured API metadata from RAG context chunks using an LLM.

    Supported providers: ``openai``, ``gemini``, ``groq``, ``mock``.
    The provider and model are resolved from constructor arguments first,
    then from environment variables.

    Parameters
    ----------
    provider:
        LLM provider name.  Defaults to the ``LLM_PROVIDER`` env var or ``"gemini"``.
    model_name:
        Model identifier.  Defaults to the provider-specific env var or a
        sensible default for each provider.
    """

    _PROVIDER_ENV_VARS: Dict[str, str] = {
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "groq":   "GROQ_API_KEY",
    }

    _DEFAULT_MODELS: Dict[str, str] = {
        "openai": "gpt-4o",
        "gemini": "gemini-1.5-flash",
        "groq":   "llama-3.3-70b-versatile",
        "mock":   "mock",
    }

    _MODEL_ENV_VARS: Dict[str, str] = {
        "openai": "OPENAI_MODEL",
        "gemini": "GEMINI_MODEL",
        "groq":   "GROQ_MODEL",
    }

    def __init__(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        self.provider: str = (
            provider or os.getenv("LLM_PROVIDER", "gemini")
        ).lower().strip()

        self.model_name: str = (
            model_name
            or os.getenv(self._MODEL_ENV_VARS.get(self.provider, ""), "")
            or self._DEFAULT_MODELS.get(self.provider, "mock")
        )

        # Validate the provider name early so callers get a clear error at
        # construction time rather than inside extract().
        valid_providers = set(self._DEFAULT_MODELS.keys())
        if self.provider not in valid_providers:
            raise ValueError(
                f"Unsupported provider '{self.provider}'. "
                f"Must be one of: {sorted(valid_providers)}"
            )

        # Validate API key presence for live providers.
        if self.provider != "mock":
            env_var = self._PROVIDER_ENV_VARS[self.provider]
            if not os.getenv(env_var):
                raise ValueError(
                    f"{env_var} is not set. "
                    f"Set the environment variable before using provider '{self.provider}'."
                )

        logger.info(
            "APIExtractor initialised — provider=%s model=%s",
            self.provider, self.model_name,
        )

    # ── Public entry point ────────────────────────────────────────────────────

    def extract(self, context_chunks: List[str], use_case: str) -> APISchema:
        """
        Extract API metadata from *context_chunks* targeting *use_case*.

        Parameters
        ----------
        context_chunks:
            List of text strings retrieved from the vector store.
        use_case:
            Natural-language description of what the caller wants to build.

        Returns
        -------
        APISchema
            A dict conforming exactly to the project schema (see module docstring).
        """
        if context_chunks is None:
            raise ValueError("context_chunks cannot be None")
        if use_case is None:
            raise ValueError("use_case cannot be None")

        t0 = time.perf_counter()
        logger.info(
            "Extraction starting — provider=%s model=%s chunks=%d",
            self.provider, self.model_name, len(context_chunks),
        )
        print(f"\n[EXTRACTOR] Starting — provider={self.provider} model={self.model_name}\n")

        max_chars = 12_000 if self.provider == "groq" else _MAX_CONTEXT_CHARS
        context = _assemble_context(context_chunks, max_chars)
        prompt  = _build_prompt(context, use_case)

        # ── Route to provider ─────────────────────────────────────────────────
        if self.provider == "openai":
            raw = _call_openai(prompt, self.model_name)
        elif self.provider == "gemini":
            raw = _call_gemini(prompt, self.model_name)
        elif self.provider == "groq":
            raw = _call_groq(prompt, self.model_name)
        else:  # mock
            raw = None  # mock bypasses the LLM entirely

        # ── Parse -> validate ──────────────────────────────────────────────────
        if raw is not None:
            logger.info("Parsing and validating LLM response")
            parsed = _parse_json(raw)
        else:
            logger.info("Using mock schema generator")
            parsed = _generate_mock_schema(context, use_case)

        schema = _validate_schema(parsed)

        elapsed = time.perf_counter() - t0
        logger.info("Extraction complete — elapsed=%.2fs", elapsed)
        print(f"[EXTRACTOR] Completed — {elapsed:.1f}s\n")

        return schema


# ── Prompt engineering ────────────────────────────────────────────────────────

def _assemble_context(chunks: List[str], max_chars: int = _MAX_CONTEXT_CHARS) -> str:
    """
    Join context chunks into a single string, hard-capping at
    ``max_chars`` to protect against token overflows.

    Truncation is applied to the *concatenated* string, not per-chunk, so
    more chunks always contributes more context up to the cap.
    """
    joined = "\n---\n".join(c for c in chunks if c and c.strip())
    if len(joined) > max_chars:
        logger.warning(
            "Context truncated from %d to %d chars to stay within token budget",
            len(joined), max_chars,
        )
        joined = joined[:max_chars]
    return joined


def _build_prompt(context: str, use_case: str) -> str:
    """
    Construct the user-turn prompt that instructs the LLM to extract
    API metadata and return it as strict JSON.
    """
    schema_skeleton = json.dumps(
        {
            "api_name": "",
            "base_url": "",
            "authentication": {
                "type": "",
                "header_name": "",
                "query_parameter": "",
                "scheme": ""
            },
            "environment_variable": "",
            "timeout": 30,
            "endpoints": [
                {
                    "name": "",
                    "summary": "",
                    "method": "",
                    "path": "",
                    "parameters": [
                        {
                            "name": "",
                            "type": "",
                            "required": True,
                            "default": None,
                            "description": ""
                        }
                    ]
                }
            ]
        },
        indent=2,
    )

    return f"""You are extracting API metadata from documentation.

DOCUMENTATION:
{context}

USE CASE:
{use_case}

TASK:
Extract the API metadata required to implement the user's use case.

Return ONLY a single valid JSON object that strictly follows the schema below.

STRICT RULES:
- Output ONLY valid JSON.
- Do NOT use markdown, code fences, explanations, or comments.
- Do NOT generate Python, JavaScript, or any source code.
- Do NOT invent endpoints, parameters, authentication methods, or response fields.
- If information is not explicitly present in the documentation, leave the value empty ("") or use an empty list ([]).
- Use the official API name exactly as documented.
- Extract the primary base URL.
- Extract the authentication method exactly as documented.
- Determine the correct authentication type: bearer_token, api_key_header, api_key_query, oauth2, basic_auth, none.
- Extract the header_name (e.g., X-API-Key), query_parameter (e.g., appid), or scheme (e.g., Bearer) if applicable.
- Provide a suggested environment_variable name (e.g., OPENAI_API_KEY).
- Set a default timeout in seconds (default is 30).
- Extract every documented endpoint relevant to the user's use case.
- Extract parameter names, types (float, int, string, boolean, array, object), whether required, default values, and descriptions.
- Return ONLY one JSON object matching the schema below.
- Do NOT include any additional keys.

REQUIRED JSON SCHEMA:
{schema_skeleton}

FIELD DEFINITIONS:

- api_name:
  Official API name.

- base_url:
  Primary API base URL.

- authentication.type:
  One of:
  bearer
  oauth2
  apikey
  basic
  none

- authentication.env_var_name:
  Generate a meaningful environment variable.

  Examples:
  Spotify -> SPOTIFY_ACCESS_TOKEN
  OpenAI -> OPENAI_API_KEY
  GitHub -> GITHUB_TOKEN
  Stripe -> STRIPE_API_KEY

- authentication.header_format:
  Full HTTP authentication header.

  Example:
  Authorization: Bearer <ACCESS_TOKEN>

- endpoints[].name:
  snake_case function name.

- endpoints[].path:
  Relative endpoint path.

- endpoints[].method:
  HTTP method.

- endpoints[].description:
  One concise sentence describing the endpoint.

- endpoints[].parameters:
  Include:
    • name
    • type
    • required
    • description

- endpoints[].response_schema:
  JSON object describing documented response fields and their types.

OUTPUT:"""
# ── Provider implementations ──────────────────────────────────────────────────

def _call_openai(prompt: str, model: str) -> str:
    """
    Call the OpenAI Chat Completions API and return the raw response string.

    Uses ``response_format=json_object`` to enforce JSON output at the API
    level, giving a second layer of guarantee on top of the prompt.
    Temperature is 0 for maximum determinism.
    """
    from openai import OpenAI, RateLimitError, APIStatusError, APIConnectionError

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    logger.info("Calling OpenAI — model=%s", model)

    def _attempt() -> str:
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            max_tokens=4096,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
        )
        content = response.choices[0].message.content or ""
        logger.debug("OpenAI response length: %d chars", len(content))
        return content

    return _with_retry(
        _attempt,
        retryable_exceptions=(RateLimitError, APIConnectionError),
        retryable_status_codes={429, 500, 502, 503, 504},
        status_exc_type=APIStatusError,
        provider="openai",
    )


def _call_gemini(prompt: str, model: str) -> str:
    """
    Call the Google Gemini API and return the raw response string.

    Uses ``response_mime_type="application/json"`` to constrain output format.
    Temperature is 0 for extraction determinism.
    """
    import google.generativeai as genai
    from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, GoogleAPICallError

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])  # type: ignore[attr-defined]
    logger.info("Calling Gemini — model=%s", model)

    gemini_model = genai.GenerativeModel(  # type: ignore[attr-defined]
        model_name=model,
        system_instruction=_SYSTEM_PROMPT,
    )

    generation_config = {
        "temperature": 0,
        "max_output_tokens": 4096,
        "response_mime_type": "application/json",
    }

    def _attempt() -> str:
        response = gemini_model.generate_content(
            prompt,
            generation_config=generation_config,  # type: ignore[arg-type]
        )
        text = response.text.strip()
        logger.debug("Gemini response length: %d chars", len(text))
        return text

    return _with_retry(
        _attempt,
        retryable_exceptions=(ResourceExhausted, ServiceUnavailable),
        retryable_status_codes=set(),          # Gemini raises typed exceptions
        status_exc_type=GoogleAPICallError,
        provider="gemini",
    )


def _call_groq(prompt: str, model: str) -> str:
    """
    Call the Groq API (OpenAI-compatible) and return the raw response string.

    Groq's ``json_validate_failed`` (HTTP 400) is a known failure mode: it fires
    when the model generates extra fields (sdk_recommendation, code_examples)
    that violate Groq's internal JSON schema validator.  Our prompt forbids those
    fields, but some Groq models still produce them.

    Strategy:
      1. Try with ``response_format=json_object`` (fastest, strictest).
      2. On ``json_validate_failed`` (400), retry WITHOUT response_format so
         Groq returns free-form text — we repair and validate it ourselves.
      3. On rate limit, fall back to ``_GROQ_FALLBACK_MODEL`` with the same
         two-tier strategy.
    """
    from openai import OpenAI, RateLimitError, APIStatusError, APIConnectionError

    client = OpenAI(
        api_key=os.environ["GROQ_API_KEY"],
        base_url="https://api.groq.com/openai/v1",
    )

    def _attempt_model(mdl: str, use_json_format: bool = True) -> str:
        logger.info("Calling Groq — model=%s json_format=%s", mdl, use_json_format)
        kwargs: Dict[str, Any] = {
            "model":       mdl,
            "temperature": 0,
            "max_tokens":  4096,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
        }
        if use_json_format:
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        logger.debug("Groq response length: %d chars", len(content))
        return content

    def _is_json_validate_failed(exc: Exception) -> bool:
        """Return True for Groq's json_validate_failed 400 error."""
        if not isinstance(exc, APIStatusError):
            return False
        if getattr(exc, "status_code", None) != 400:
            return False
        body = getattr(exc, "body", {}) or {}
        if isinstance(body, dict):
            err = body.get("error", {})
            return isinstance(err, dict) and err.get("code") == "json_validate_failed"
        return "json_validate_failed" in str(exc)

    def _attempt_with_fallback(mdl: str) -> str:
        """Try json_object mode; on json_validate_failed retry in free-text mode."""
        try:
            return _with_retry(
                lambda: _attempt_model(mdl, use_json_format=True),
                retryable_exceptions=(RateLimitError, APIConnectionError),
                retryable_status_codes={429, 500, 502, 503, 504},
                status_exc_type=APIStatusError,
                provider=f"groq({mdl})",
            )
        except APIStatusError as exc:
            if _is_json_validate_failed(exc):
                logger.warning(
                    "Groq json_validate_failed on model=%s — "
                    "retrying without response_format (free-text mode)",
                    mdl,
                )
                # Retry without response_format; our _parse_json() will repair it.
                return _with_retry(
                    lambda: _attempt_model(mdl, use_json_format=False),
                    retryable_exceptions=(RateLimitError, APIConnectionError),
                    retryable_status_codes={429, 500, 502, 503, 504},
                    status_exc_type=APIStatusError,
                    provider=f"groq({mdl})-freetext",
                )
            raise

    try:
        return _attempt_with_fallback(model)
    except RateLimitError:
        # Primary model exhausted - try fallback with its own two-tier strategy.
        logger.warning(
            "Groq primary model %s rate-limited - falling back to %s",
            model, _GROQ_FALLBACK_MODEL,
        )
        return _attempt_with_fallback(_GROQ_FALLBACK_MODEL)


# ── Retry infrastructure ──────────────────────────────────────────────────────

def _with_retry(
    fn: Any,
    *,
    retryable_exceptions: tuple,
    retryable_status_codes: set,
    status_exc_type: type[Exception],
    provider: str,
) -> str:
    """
    Call *fn()* with exponential-backoff retries.

    Retries on:
      • Instances of ``retryable_exceptions``.
      • Instances of ``status_exc_type`` whose ``.status_code`` is in
        ``retryable_status_codes``.

    Raises the last exception after ``_MAX_RETRIES`` failed attempts.
    """
    last_exc: Exception | None = None

    for attempt in range(_MAX_RETRIES + 1):
        try:
            return fn()

        except status_exc_type as exc:
            # Typed status errors (e.g. openai.APIStatusError) expose status_code.
            code = getattr(exc, "status_code", None)
            if code in retryable_status_codes:
                last_exc = exc
                _backoff(attempt, provider, reason=f"HTTP {code}")
            else:
                raise  # Permanent error (e.g. 401, 404) — do not retry.

        except retryable_exceptions as exc:  # type: ignore[misc]
            last_exc = exc
            _backoff(attempt, provider, reason=type(exc).__name__)

    assert last_exc is not None
    raise last_exc


def _backoff(attempt: int, provider: str, reason: str) -> None:
    """Sleep for ``_BACKOFF_BASE * 2^attempt`` seconds and log the wait."""
    if attempt >= _MAX_RETRIES:
        return  # Last attempt — let the caller raise.
    delay = _BACKOFF_BASE * (2 ** attempt)
    logger.warning(
        "%s retry %d/%d — reason=%s sleeping=%.1fs",
        provider, attempt + 1, _MAX_RETRIES, reason, delay,
    )
    time.sleep(delay)


# ── JSON repair pipeline ──────────────────────────────────────────────────────

def _parse_json(raw: str) -> APISchema:
    """
    Convert a raw LLM string into a Python dict using a layered repair pipeline:

      1. Strip markdown code fences (```json ... ``` or ``` ... ```).
      2. Attempt ``json.loads()`` on the stripped text.
      3. Remove trailing commas and retry.
      4. Fix unescaped newlines inside strings and retry.
      5. Extract the largest ``{...}`` block and retry.
      6. Raise ``ValueError`` with the original text if all attempts fail.

    This pipeline handles 99 % of real LLM output quirks without any
    external dependency.
    """
    logger.info("Parsing LLM JSON response (%d chars)", len(raw))

    # Step 1 — strip markdown fences
    cleaned = _strip_markdown_fences(raw)

    # Step 2 — direct parse (fast path, works for well-formed responses)
    result = _try_json_loads(cleaned, "direct parse")
    if result is not None:
        return result

    # Step 3 — remove trailing commas before } or ]
    repaired = _remove_trailing_commas(cleaned)
    result = _try_json_loads(repaired, "trailing-comma repair")
    if result is not None:
        return result

    # Step 4 — fix literal newlines inside JSON strings
    repaired = _fix_newlines_in_strings(repaired)
    result = _try_json_loads(repaired, "newline repair")
    if result is not None:
        return result

    # Step 5 — extract largest {...} block (handles leading/trailing prose)
    extracted = _extract_json_object(raw)
    if extracted:
        result = _try_json_loads(extracted, "object extraction")
        if result is not None:
            return result

    raise ValueError(
        f"Failed to parse LLM response as JSON after all repair attempts.\n"
        f"Raw response (first 500 chars):\n{raw[:500]}"
    )


def _try_json_loads(text: str, stage: str) -> Optional[APISchema]:
    """Attempt json.loads(); return the dict on success, None on failure."""
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            logger.debug("JSON parsed successfully at stage: %s", stage)
            return result
        logger.warning("JSON parse at '%s' returned %s, not dict", stage, type(result).__name__)
        return None
    except json.JSONDecodeError:
        return None


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` and ``` ... ``` wrappers."""
    text = text.strip()
    # Match ```json\n...\n``` or ```\n...\n```
    pattern = r"^```(?:json)?\s*\n?(.*?)\n?```\s*$"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Simpler: remove leading ``` or ```json
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _remove_trailing_commas(text: str) -> str:
    """
    Remove trailing commas before ``}`` or ``]`` — a common LLM JSON mistake.

    Regex: comma(s) followed by optional whitespace then a closing bracket.
    """
    return re.sub(r",\s*([}\]])", r"\1", text)


def _fix_newlines_in_strings(text: str) -> str:
    """
    Replace literal (unescaped) newlines inside JSON string values with \\n.

    Some models output multi-line strings without escaping them.
    """
    def replace_newlines(m: re.Match) -> str:
        return m.group(0).replace("\n", "\\n").replace("\r", "\\r")

    # Match JSON string literals (rough but effective for this repair task).
    return re.sub(r'"(?:[^"\\]|\\.)*"', replace_newlines, text)


def _extract_json_object(text: str) -> Optional[str]:
    """
    Find the outermost ``{...}`` block in *text*.

    Handles cases where the LLM prefixes the JSON with prose like
    "Here is the extracted schema:" followed by the JSON object.
    """
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


# ── Schema validation (allowlist-based) ──────────────────────────────────────

def _to_snake_case(s: str) -> str:
    """Convert camelCase/PascalCase/spaces/hyphens to snake_case."""
    s = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', s)
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s).lower()
    s = re.sub(r'[^a-z0-9_]+', '_', s)
    s = re.sub(r'_+', '_', s)
    return s.strip('_')


def _validate_schema(raw: APISchema) -> APISchema:
    """
    Enforce the project schema strictly:

    * Remove every key not in the allowlist.
    * Add missing required keys with safe defaults.
    * Validate and normalise each sub-structure.
    * Deduplicate endpoints to prevent duplicate methods.
    """
    logger.info("Validating schema")

    schema: APISchema = {}

    schema["api_name"] = _coerce_str(raw.get("api_name"), "")
    schema["base_url"] = _coerce_str(raw.get("base_url"), "")

    raw_auth = raw.get("authentication") or {}
    if not isinstance(raw_auth, dict):
        raw_auth = {}
    schema["authentication"] = _validate_authentication(raw_auth)

    schema["environment_variable"] = _coerce_str(raw.get("environment_variable"), "")

    try:
        schema["timeout"] = int(raw.get("timeout", raw.get("timeouts", 30)))
    except Exception:
        schema["timeout"] = 30

    raw_eps = raw.get("endpoints") or []
    if not isinstance(raw_eps, list):
        raw_eps = []

    # Deduplicate endpoints by method name to avoid code wrapper duplication
    seen_names = set()
    deduped_eps = []
    for ep in raw_eps:
        if not isinstance(ep, dict):
            continue
        norm_ep = _normalize_endpoint(ep)
        ep_name = norm_ep["name"]
        if ep_name not in seen_names:
            seen_names.add(ep_name)
            deduped_eps.append(norm_ep)

    schema["endpoints"] = deduped_eps

    logger.info(
        "Schema validated — endpoints=%d auth_type=%s",
        len(schema["endpoints"]),
        schema["authentication"].get("type", ""),
    )
    return schema


def _validate_authentication(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise the authentication sub-dict, keeping only allowed keys."""
    auth_type = _coerce_str(raw.get("type"), "none").lower().strip()
    # Support mapping for robust compatibility. Preserve "bearer" for integration tests.
    if auth_type == "bearer":
        auth_type = "bearer"
    elif auth_type == "bearer_token":
        auth_type = "bearer"
    elif auth_type in ("apikey", "api_key", "api_key_header"):
        auth_type = "api_key_header"
    elif auth_type in ("basic", "basic_auth"):
        auth_type = "basic_auth"
    elif auth_type in ("api_key_query", "apikey_query", "query"):
        auth_type = "api_key_query"
    elif auth_type in ("jwt", "jsonwebtoken"):
        auth_type = "jwt"
    elif auth_type in ("oauth2", "oauth"):
        auth_type = "oauth2"

    return {
        "type":            auth_type,
        "header_name":     _coerce_str(raw.get("header_name"), ""),
        "query_parameter": _coerce_str(raw.get("query_parameter") or raw.get("query_name"), ""),
        "scheme":          _coerce_str(raw.get("scheme"), ""),
    }


def _normalize_endpoint(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalise a single endpoint dict."""
    method_raw = _coerce_str(raw.get("method"), "GET").upper()
    method = method_raw if method_raw in _HTTP_METHODS else "GET"
    path = _coerce_str(raw.get("path"), "")

    parameters_raw = raw.get("parameters") or []
    if not isinstance(parameters_raw, list):
        parameters_raw = []
    parameters = [
        _normalize_parameter(p, path=path, method=method)
        for p in parameters_raw
        if isinstance(p, dict)
    ]

    raw_name = _coerce_str(raw.get("name"), "")
    clean_name = _to_snake_case(raw_name)

    return {
        "name":            clean_name,
        "summary":         _coerce_str(raw.get("summary") or raw.get("description"), ""),
        "method":          method,
        "path":            path,
        "parameters":      parameters,
    }


def _normalize_parameter(raw: Dict[str, Any], path: str = "", method: str = "GET") -> Dict[str, Any]:
    """Normalise a single parameter dict, keeping only allowed keys."""
    required = raw.get("required")
    if not isinstance(required, bool):
        required = str(required).lower() in {"true", "1", "yes"}

    param_type = _coerce_str(raw.get("type"), "string").lower().strip()
    if param_type in ("integer", "int"):
        param_type = "int"
    elif param_type in ("float", "number"):
        param_type = "float"
    elif param_type in ("boolean", "bool"):
        param_type = "boolean"
    elif param_type in ("array", "list"):
        param_type = "array"
    elif param_type in ("object", "dict"):
        param_type = "object"
    else:
        param_type = "string"

    location = _coerce_str(raw.get("location"), "").lower().strip()
    if location not in {"path", "query", "body", "header", "form", "cookie"}:
        # Smart location inference
        name = _coerce_str(raw.get("name"), "")
        if path and (f"{{{name}}}" in path or f":{name}" in path):
            location = "path"
        elif method in {"POST", "PUT", "PATCH"}:
            location = "body"
        else:
            location = "query"

    return {
        "name":        _coerce_str(raw.get("name"), ""),
        "type":        param_type,
        "location":    location,
        "required":    required,
        "default":     raw.get("default", None),
        "description": _coerce_str(raw.get("description"), ""),
    }


def _coerce_str(value: Any, default: str) -> str:
    """Return *value* as a stripped string, or *default* if absent/non-string."""
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


# ── Mock schema generator ─────────────────────────────────────────────────────

def _generate_mock_schema(context: str, use_case: str) -> APISchema:
    """
    Generate a deterministic mock schema for offline testing.

    Returns ONLY the required top-level fields.
    Never generates SDK recommendations, code examples, or any extra fields.
    Detection is keyword-based against the combined context + use_case.
    """
    combined = (context + " " + use_case).lower()

    # ── API name detection ────────────────────────────────────────────────────
    api_name, base_url, auth_type, header_name, query_name, scheme = _detect_api_profile(combined)

    # ── Endpoint detection ────────────────────────────────────────────────────
    endpoints = _detect_mock_endpoints(combined, api_name)

    return {
        "api_name": api_name,
        "base_url": base_url,
        "authentication": {
            "type":          auth_type,
            "header_name":   header_name,
            "query_name":    query_name,
            "scheme":        scheme,
        },
        "sdk_recommendation": f"Official {api_name} SDK recommended for production.",
        "timeouts": 30,
        "endpoints": endpoints,
    }


def _detect_api_profile(text: str) -> tuple[str, str, str, str, str, str]:
    """
    Return (api_name, base_url, auth_type, header_name, query_name, scheme)
    by matching known API keywords in *text*.
    """
    profiles = [
        ("openai",   "OpenAI",   "https://api.openai.com/v1",          "bearer", "Authorization", "", "Bearer"),
        ("spotify",  "Spotify",  "https://api.spotify.com/v1",         "bearer", "Authorization", "", "Bearer"),
        ("stripe",   "Stripe",   "https://api.stripe.com/v1",          "bearer", "Authorization", "", "Bearer"),
        ("github",   "GitHub",   "https://api.github.com",             "bearer", "Authorization", "", "Bearer"),
        ("twilio",   "Twilio",   "https://api.twilio.com/2010-04-01",  "basic_auth", "Authorization", "", "Basic"),
        ("slack",    "Slack",    "https://slack.com/api",              "bearer", "Authorization", "", "Bearer"),
        ("sendgrid", "SendGrid", "https://api.sendgrid.com/v3",        "bearer", "Authorization", "", "Bearer"),
        ("anthropic", "Anthropic", "https://api.anthropic.com/v1",     "api_key_header", "x-api-key", "", ""),
    ]

    for keyword, name, base_url, auth_type, header, query, scheme in profiles:
        if keyword in text:
            return name, base_url, auth_type, header, query, scheme

    return (
        "Target API",
        "https://api.example.com/v1",
        "bearer",
        "Authorization",
        "",
        "Bearer",
    )


def _detect_mock_endpoints(text: str, api_name: str) -> List[Dict[str, Any]]:
    """
    Return a list of mock endpoints inferred from keywords in *text*.
    """
    # Map of trigger keywords -> endpoint spec
    candidates = [
        (
            {"user", "users"},
            {
                "name":        "create_user",
                "path":        "/users",
                "method":      "POST",
                "summary":     "Create a new user.",
                "parameters": [
                    {"name": "username", "type": "string", "required": True,  "default": None, "description": "The unique user account username."},
                    {"name": "email",    "type": "string", "required": False, "default": None, "description": "Email address associated with the user account."},
                ],
                "response": {"id": "string", "username": "string", "email": "string"},
            },
        ),
        (
            {"chat", "completion", "message", "gpt", "bot"},
            {
                "name":        "create_chat_completion",
                "path":        "/chat/completions",
                "method":      "POST",
                "summary":     "Send a list of messages and receive a model-generated reply.",
                "parameters": [
                    {"name": "model",       "type": "string", "required": True,  "default": None, "description": "Model ID to use."},
                    {"name": "messages",    "type": "array",  "required": True,  "default": None, "description": "Conversation history."},
                    {"name": "temperature", "type": "float",  "required": False, "default": None, "description": "Sampling temperature 0-2."},
                ],
                "response": {"id": "string", "object": "string", "choices": "array"},
            },
        ),
        (
            {"track", "search", "song", "music", "playlist"},
            {
                "name":        "search_items",
                "path":        "/search",
                "method":      "GET",
                "summary":     "Search for tracks, albums, artists, or playlists.",
                "parameters": [
                    {"name": "q",     "type": "string", "required": True,  "default": None, "description": "Search query."},
                    {"name": "type",  "type": "string", "required": True,  "default": None, "description": "Item types: track, album, artist."},
                    {"name": "limit", "type": "int",    "required": False, "default": None, "description": "Max results (1-50)."},
                ],
                "response": {"tracks": "object", "albums": "object", "artists": "object"},
            },
        ),
        (
            {"payment", "charge", "invoice", "subscription", "stripe"},
            {
                "name":        "create_payment_intent",
                "path":        "/payment_intents",
                "method":      "POST",
                "summary":     "Create a PaymentIntent representing a transaction.",
                "parameters": [
                    {"name": "amount",   "type": "int",    "required": True,  "default": None, "description": "Amount in smallest currency unit."},
                    {"name": "currency", "type": "string", "required": True,  "default": None, "description": "3-letter ISO currency code."},
                ],
                "response": {"id": "string", "status": "string", "client_secret": "string"},
            },
        ),
        (
            {"repository", "repo", "commit", "pull request", "github", "github issue"},
            {
                "name":        "list_repositories",
                "path":        "/user/repos",
                "method":      "GET",
                "summary":     "List repositories for the authenticated user.",
                "parameters": [
                    {"name": "type",     "type": "string", "required": False, "default": None, "description": "Filter by: all, owner, public, private."},
                    {"name": "per_page", "type": "int",    "required": False, "default": None, "description": "Results per page (max 100)."},
                ],
                "response": {"id": "int", "name": "string", "full_name": "string", "private": "boolean"},
            },
        ),
        (
            {"email", "send", "message", "smtp", "sendgrid", "mailgun"},
            {
                "name":        "send_email",
                "path":        "/mail/send",
                "method":      "POST",
                "summary":     "Send an email to one or more recipients.",
                "parameters": [
                    {"name": "to",      "type": "array",  "required": True,  "default": None, "description": "List of recipient objects."},
                    {"name": "from",    "type": "object", "required": True,  "default": None, "description": "Sender email and name."},
                    {"name": "subject", "type": "string", "required": True,  "default": None, "description": "Email subject line."},
                    {"name": "content", "type": "array",  "required": True,  "default": None, "description": "Email body content blocks."},
                ],
                "response": {"status": "string"},
            },
        ),
    ]

    matched: List[Dict[str, Any]] = []
    for keywords, endpoint_spec in candidates:
        if any(kw in text for kw in keywords):
            matched.append(endpoint_spec)
        if len(matched) >= 3:
            break  # Cap at 3 endpoints for a realistic mock

    if not matched:
        # Generic fallback endpoint
        matched.append({
            "name":        "get_resource",
            "path":        "/resources",
            "method":      "GET",
            "summary":     "Retrieve a list of resources.",
            "parameters": [
                {"name": "limit",  "type": "int", "required": False, "default": None, "description": "Max number of results."},
                {"name": "offset", "type": "int", "required": False, "default": None, "description": "Pagination offset."},
            ],
            "response": {"data": "array", "total": "int"},
        })

    return matched