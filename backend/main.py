import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.routes import router

if sys.platform == 'win32':
    try:
        if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-load embedding model to avoid query delay during api generation
    print("Warming up embedding model on startup...")
    try:
        from rag.embeddings import EmbeddingClient
        client = EmbeddingClient()
        _ = client.model
        print("Embedding model loaded and ready.")
    except Exception as e:
        print(f"Failed to pre-load embedding model: {e}")
    yield

app = FastAPI(
    title="Smart Devtool for API",
    description="Backend service for crawling, parsing API docs and generating wrapper code using RAG and LLMs.",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static folder
static_dir = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Mount React build assets if they exist
dist_dir = os.path.join(BASE_DIR, "frontend", "dist")
dist_assets_dir = os.path.join(dist_dir, "assets")
if os.path.exists(dist_assets_dir):
    app.mount("/assets", StaticFiles(directory=dist_assets_dir), name="assets")

# Include router
app.include_router(router)

@app.get("/")
async def root():
    dist_index = os.path.join(BASE_DIR, "frontend", "dist", "index.html")
    if os.path.exists(dist_index):
        return FileResponse(dist_index)
    index_path = os.path.join(BASE_DIR, "frontend", "index.html")
    return FileResponse(index_path)


if __name__ == "__main__":
    import uvicorn
    import argparse
    
    parser = argparse.ArgumentParser(description="Smart Devtool for API Server")
    parser.add_argument("--server", action="store_true", help="Start the FastAPI backend server")
    args = parser.parse_args()
    
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    print(f"Starting API Server on http://{host}:{port}...")
    uvicorn.run("main:app", host=host, port=port, reload=True)
