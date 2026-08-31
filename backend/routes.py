import uuid
import logging
import os
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Import pipeline components
from crawler.crawler import APIDocCrawler
from parser.cleaner import HTMLCleaner
from rag.chunker import MarkdownChunker
from rag.embeddings import EmbeddingClient
from rag.retriever import VectorStoreManager
from llm.extractor import APIExtractor
from llm.chatbot import ConversationalChatbot
from generator.wrapper_generator import WrapperGenerator

logger = logging.getLogger("smart_devtool.routes")

router = APIRouter(prefix="/api/v1")

# Global in-memory dictionary to track crawl background jobs
CRAWL_JOBS: Dict[str, Dict[str, Any]] = {}

# Pydantic schemas for requests and responses
class CrawlRequest(BaseModel):
    url: str = Field(..., description="API Documentation URL to crawl")
    max_depth: int = Field(2, ge=1, le=5, description="Maximum link recursion depth")

class CrawlResponse(BaseModel):
    status: str
    message: str
    crawl_id: str
    total_pages_found: int

class GenerationRequest(BaseModel):
    crawl_id: str = Field(..., description="Target crawl ID containing documents collection")
    use_case: str = Field(..., description="Specific developer integration use-case (e.g. Build a chatbot)")
    target_language: str = Field("python", description="Code output language (python or javascript)")

class GenerationResponse(BaseModel):
    status: str
    wrapper_code: str
    target_language: str
    schema_details: Dict[str, Any]

class StatusResponse(BaseModel):
    crawl_id: str
    status: str
    pages_indexed: int
    current_action: str
    error: Optional[str] = None

class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of message sender: 'user' or 'assistant'")
    content: str = Field(..., description="Message content text")

class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="Conversational message history")
    provider: Optional[str] = Field(None, description="LLM provider override (gemini, openai, groq, mock)")
    crawl_id: Optional[str] = Field(None, description="Active crawl ID containing documents collection")


async def run_crawl_pipeline(crawl_id: str, url: str, max_depth: int):
    """
    Background worker function that executes crawls, cleans the markup,
    chunks text, embeds vectors, and indexes details inside ChromaDB.
    """
    job = CRAWL_JOBS[crawl_id]
    try:
        # 1. Start crawling
        job["status"] = "processing"
        job["current_action"] = "Crawling web pages"
        logger.info(f"Crawl pipeline started for {url} with ID {crawl_id}")
        
        crawler = APIDocCrawler(max_depth=max_depth)
        raw_pages = await crawler.crawl(url)
        
        if not raw_pages:
            raise ValueError("No pages were found or crawled. Please verify the URL or network access.")
            
        job["pages_indexed"] = len(raw_pages)
        job["current_action"] = "Cleaning and parsing HTML"
        
        # 2. Clean HTML content
        cleaner = HTMLCleaner()
        cleaned_pages = []
        for page in raw_pages:
            if page is None:
                raise ValueError("Encountered None page entry in crawl results list")
                
            html_content = page.get("html")
            if html_content is None:
                raise ValueError(f"Crawled page entry for URL {page.get('url')} is missing 'html' content")
                
            cleaned_text = cleaner.clean(html_content)
            
            metadata = page.get("metadata")
            title = metadata.get("title", "") if isinstance(metadata, dict) else ""
            
            cleaned_pages.append({
                "url": page.get("url"),
                "markdown": cleaned_text,
                "title": title
            })
            
        job["current_action"] = "Chunking markdown documents"
        
        # 3. Create document chunks
        print("\n[CHUNKER]\nStarting...\n")
        import time
        chunker_start = time.time()
        
        chunker = MarkdownChunker()
        all_chunks = []
        for page in cleaned_pages:
            chunks = chunker.split(page["markdown"])
            # Inject page URL source details to chunks
            for chunk in chunks:
                chunk["source_url"] = page.get("url")
                all_chunks.append(chunk)
                
        if not all_chunks:
            raise ValueError("Document cleaning yielded no indexable text chunks.")
            
        # Save chunks.json
        import json
        import os
        os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
        chunks_path = os.path.join(BASE_DIR, "data", "chunks.json")
        with open(chunks_path, "w", encoding="utf-8") as f:
            json.dump(all_chunks, f, indent=2)
            
        chunker_elapsed = time.time() - chunker_start
        print(f"\n[CHUNKER]\n\nLoaded\n\n{len(cleaned_pages)} markdown files\n\nCreated\n\n{len(all_chunks)} chunks\n\nSaved\n\nchunks.json\n\nTime: {chunker_elapsed:.1f}s\n")
            
        job["current_action"] = "Generating vector embeddings"
        
        # 4. Embed chunks
        embedder = EmbeddingClient()
        chunk_texts = [c["text"] for c in all_chunks]
        embeddings = embedder.get_embeddings(chunk_texts)
        
        job["current_action"] = "Indexing vectors in ChromaDB"
        
        # 5. Index in Vector DB
        retriever = VectorStoreManager()
        retriever.add_documents(
            collection_name=crawl_id,
            chunks=all_chunks,
            embeddings=embeddings
        )
        
        # 6. Update job status
        job["status"] = "completed"
        job["current_action"] = "Done"
        logger.info(f"Crawl pipeline completed successfully for ID {crawl_id}")
        
    except Exception as e:
        logger.exception(f"Crawl pipeline failed for ID {crawl_id}: {str(e)}")
        job["status"] = "failed"
        job["current_action"] = "Error"
        job["error"] = str(e)


@router.post("/crawl", response_model=CrawlResponse)
async def start_crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
    """
    Triggers an asynchronous document indexing job for the target URL.
    Returns a unique crawl_id that can be polled for progress.
    """
    crawl_id = str(uuid.uuid4())
    
    # Register job tracker
    CRAWL_JOBS[crawl_id] = {
        "crawl_id": crawl_id,
        "status": "queued",
        "pages_indexed": 0,
        "current_action": "Queued in queue",
        "error": None
    }
    
    # Enqueue background task
    background_tasks.add_task(
        run_crawl_pipeline,
        crawl_id=crawl_id,
        url=request.url,
        max_depth=request.max_depth
    )
    
    return CrawlResponse(
        status="success",
        message="Crawling and indexing pipeline initiated in the background.",
        crawl_id=crawl_id,
        total_pages_found=0
    )


@router.get("/status/{crawl_id}", response_model=StatusResponse)
async def get_status(crawl_id: str):
    """Retrieves progress and stats of an active crawl job."""
    job = CRAWL_JOBS.get(crawl_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Crawl job '{crawl_id}' not found.")
        
    return StatusResponse(
        crawl_id=job["crawl_id"],
        status=job["status"],
        pages_indexed=job["pages_indexed"],
        current_action=job["current_action"],
        error=job.get("error")
    )


@router.post("/generate", response_model=GenerationResponse)
async def generate_wrapper(request: GenerationRequest):
    """
    Queries ChromaDB vectors using the Use Case, extracts API parameters
    via LLM context schemas, renders code, and returns the final Wrapper.
    """
    crawl_id = request.crawl_id
    use_case = request.use_case
    lang = request.target_language.lower().strip()
    
    # 1. Verify index exists (we can check by listing jobs or validating collection in ChromaDB)
    job = CRAWL_JOBS.get(crawl_id)
    if not job:
        # Allow checking if collections exist directly in case server restarted
        retriever = VectorStoreManager()
        try:
            # Try to fetch collection to verify existence
            retriever.get_or_create_collection(crawl_id)
        except Exception:
            raise HTTPException(status_code=404, detail=f"Crawl database for crawl_id '{crawl_id}' was not found.")
    elif job["status"] != "completed":
        raise HTTPException(
            status_code=400, 
            detail=f"Crawl job is not completed. Current status: '{job['status']}'. Wait for index completion."
        )

    retriever = VectorStoreManager()
    embedder = EmbeddingClient()
    
    try:
        # 2. Embed the Use Case keyword query
        query_vector = embedder.get_embeddings([use_case])[0]
        
        # 3. Initialize Extractor to determine target LLM provider limits
        extractor = APIExtractor()
        top_k = 3 if extractor.provider == "groq" else 6

        # 4. Retrieve relevant chunks based on provider token budget
        matched_chunks = retriever.query_similarity(
            collection_name=crawl_id,
            query_embedding=query_vector,
            top_k=top_k
        )
        
        if not matched_chunks:
            raise ValueError("No matching documentation fragments could be retrieved for this Use Case query.")
            
        context_texts = [c["text"] for c in matched_chunks]
        
        # 5. Extract schema fields from matches via LLM
        extracted_schema = extractor.extract(context_texts, use_case)
        
        # 5. Render target wrapper code
        generator = WrapperGenerator()
        code_string = generator.render(extracted_schema, lang)
        
        return GenerationResponse(
            status="success",
            wrapper_code=code_string,
            target_language=lang,
            schema_details=extracted_schema
        )
        
    except Exception as e:
        logger.error(f"Wrapper generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Code generation failed: {str(e)}")


@router.post("/chat/stream")
async def chat_stream_endpoint(req: ChatCompletionRequest):
    """
    Real-time SSE / chunked streaming endpoint for conversational AI completion runs.
    """
    try:
        dict_messages = [{"role": m.role, "content": m.content} for m in req.messages]
        chatbot = ConversationalChatbot(provider=req.provider)
        
        def token_generator():
            for token in chatbot.stream_chat(dict_messages, crawl_id=req.crawl_id):
                yield token

        return StreamingResponse(token_generator(), media_type="text/plain")
    except Exception as e:
        logger.error(f"Chat stream endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

