import uvicorn
import argparse
from dotenv import load_dotenv
import os
import sys
import asyncio
from typing import Optional


# Load environment variables
load_dotenv()

# Expose app for Uvicorn CLI (e.g. uvicorn main:app --reload)
from backend.main import app


def start_server(host: Optional[str] = None, port: Optional[int] = None):
    if sys.platform == 'win32':
        try:
            if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        except Exception:
            pass
    
    if host is None:
        host = os.getenv("HOST", "127.0.0.1")
    if port is None:
        port = int(os.getenv("PORT", "8000"))
        
    reload = host == "127.0.0.1" or host == "localhost"
    print(f"Starting API Server on http://{host}:{port}...")
    uvicorn.run("backend.main:app", host=host, port=port, reload=reload)

def main():
    parser = argparse.ArgumentParser(description="Smart Devtool for API CLI")
    parser.add_argument("--server", action="store_true", help="Start the FastAPI backend server")
    parser.add_argument("--host", type=str, default=None, help="Server host binding address")
    parser.add_argument("--port", type=int, default=None, help="Server port number")
    
    args = parser.parse_args()
    
    if args.server:
        start_server(host=args.host, port=args.port)
    else:
        print("Smart Devtool for API")
        print("Use --server flag to run the backend API server.")

if __name__ == "__main__":
    main()
