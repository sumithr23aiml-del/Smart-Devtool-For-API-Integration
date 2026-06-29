import os
import re
import logging
import time
from typing import List, Dict, Any, Optional
import chromadb

logger = logging.getLogger("smart_devtool.retriever")

class VectorStoreManager:
    """
    Manages connections, collections, and semantic search operations on ChromaDB.
    """
    def __init__(self, persist_directory: Optional[str] = None):
        if persist_directory is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            persist_directory = os.path.join(base_dir, "data", "chroma")
        elif not os.path.isabs(persist_directory):
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            persist_directory = os.path.join(base_dir, persist_directory.lstrip("./"))
        self.persist_directory = persist_directory
        # Ensure data directories exist
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # Connect to persistent database client (let exceptions bubble up)
        logger.info(f"Initializing ChromaDB PersistentClient at {self.persist_directory}")
        self.client = chromadb.PersistentClient(path=self.persist_directory)

    def get_or_create_collection(self, collection_name: str):
        """Gets or creates a collection by name."""
        # Clean collection name (ChromaDB allows alphanumeric and underscores, length 3-63)
        sanitized_name = self._sanitize_collection_name(collection_name)
        return self.client.get_or_create_collection(name=sanitized_name)

    def add_documents(
        self, 
        collection_name: str, 
        chunks: List[Dict[str, Any]], 
        embeddings: List[List[float]]
    ) -> None:
        """
        Adds text chunks, metadata, vectors, and unique IDs to the specified ChromaDB collection.
        """
        if not chunks:
            return
            
        if len(chunks) != len(embeddings):
            raise ValueError(f"Mismatch between number of chunks ({len(chunks)}) and embeddings ({len(embeddings)})")

        collection = self.get_or_create_collection(collection_name)
        
        ids = []
        documents = []
        metadatas = []
        
        for idx, chunk in enumerate(chunks):
            if chunk is None:
                raise ValueError("Encountered None chunk entry in documents list")
                
            # Enforce string IDs
            ids.append(chunk.get("id", f"chunk_{idx}"))
            text = chunk.get("text", "").strip()

            if not text:
                continue

            documents.append(text)
            
            # Metadata must be simple dict with str/int/float/bool values
            raw_meta = chunk.get("metadata")
            flat_meta = {}
            if isinstance(raw_meta, dict):
                for k, v in raw_meta.items():
                    if isinstance(v, list):
                        flat_meta[k] = ", ".join(map(str, v))
                    elif isinstance(v, (str, int, float, bool)):
                        flat_meta[k] = v
                        
            # Add static page source if available
            if "source_url" in chunk:
                flat_meta["source_url"] = chunk["source_url"]
                
            metadatas.append(flat_meta)

        logger.info(f"Indexing {len(documents)} documents in collection '{collection_name}'...")

        BATCH_SIZE = 500

        for i in range(0, len(documents), BATCH_SIZE):
            collection.upsert(
                ids=ids[i:i + BATCH_SIZE],
                documents=documents[i:i + BATCH_SIZE],
                embeddings=embeddings[i:i + BATCH_SIZE],
                metadatas=metadatas[i:i + BATCH_SIZE]
            )

        logger.info("Indexing complete.")

    def query_similarity(
        self, 
        collection_name: str, 
        query_embedding: List[float], 
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Performs vector search matching in ChromaDB.
        """
        if query_embedding is None:
            raise ValueError("Query embedding cannot be None for similarity search")

        print("\n[RETRIEVER]\nStarting...\n")
        start_time = time.time()

        collection = self.get_or_create_collection(collection_name)
        
        logger.info(f"Querying collection '{collection_name}' for top-{top_k} matches...")
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        # Format results into standardized dictionary structures
        formatted_results = []
        
        if results and 'documents' in results and results['documents']:
            docs = results['documents'][0]
            ids = results['ids'][0]
            metadatas = results['metadatas'][0] if 'metadatas' in results and results['metadatas'] else [{}] * len(docs)
            distances = results['distances'][0] if 'distances' in results and results['distances'] else [0.0] * len(docs)
            
            for idx in range(len(docs)):
                dist = distances[idx]
                similarity = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
                
                formatted_results.append({
                    "chunk_id": ids[idx],
                    "text": docs[idx],
                    "metadata": metadatas[idx],
                    "score": float(similarity)
                })
                
        logger.info(f"Found {len(formatted_results)} match results.")
        
        elapsed = time.time() - start_time
        print(f"Completed\n\nTime: {elapsed:.1f}s\n")
        
        return formatted_results

    def delete_collection(self, collection_name: str) -> None:
        """Deletes a collection by name."""
        sanitized_name = self._sanitize_collection_name(collection_name)
        self.client.delete_collection(name=sanitized_name)
        logger.info(f"Deleted collection: {sanitized_name}")

    def _sanitize_collection_name(self, name: str) -> str:
        """
        ChromaDB collections rules:
        - 3 to 63 chars long.
        - Start and end with lowercase letter or number.
        - Contain only lowercase letters, numbers, underscores or hyphens.
        """
        # Replace non-alphanumeric chars with underscore
        clean = re.sub(r'[^a-zA-Z0-9_-]', '_', name).lower()
        # Strip leading/trailing underscores/hyphens
        clean = clean.strip('_-')
        # Pad if too short
        if len(clean) < 3:
            clean = f"col_{clean}"
        # Truncate if too long
        if len(clean) > 63:
            clean = clean[:63].rstrip('_-')
        return clean
