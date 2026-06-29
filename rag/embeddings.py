import os
import logging
import time
from typing import List

# Suppress noisy HuggingFace Hub unauthenticated request warnings in console output
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub.utils._headers").setLevel(logging.ERROR)

logger = logging.getLogger("smart_devtool.embeddings")


class EmbeddingClient:
    """
    Manages vector embeddings calculation for text chunks.
    Supports SentenceTransformers (local) and API configurations (Gemini/OpenAI API).
    """
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self.dimension = 384  # Default for all-MiniLM-L6-v2

    @property
    def model(self):
        """Lazy load the sentence-transformers model."""
        if self._model is None:
            provider = os.getenv("EMBEDDING_PROVIDER", "local").lower()
            if provider == "local":
                import torch
                from sentence_transformers import SentenceTransformer
                device = "cuda" if torch.cuda.is_available() else "cpu"
                logger.info(f"Loading local SentenceTransformer model: {self.model_name} on device: {device}")
                self._model = SentenceTransformer(self.model_name, device=device)
                # Use the renamed PEP-compliant method to avoid FutureWarnings
                self.dimension = self._model.get_embedding_dimension() or 384
            else:
                self._model = provider  # API provider name e.g. "gemini" or "openai"
                if provider == "openai":
                    self.dimension = 1536
                elif provider == "gemini":
                    self.dimension = 768
        return self._model

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Computes numeric embeddings vectors for a list of string chunks.
        """
        if not texts:
            return []

        print("\n[EMBEDDINGS]\nStarting...\n")
        start_time = time.time()

        model_ref = self.model
        provider = os.getenv("EMBEDDING_PROVIDER", "local").lower()

        # 1. Local SentenceTransformer
        if provider == "local" or hasattr(model_ref, "encode"):
            embeddings = model_ref.encode(texts)
            result_list = [embedding.tolist() for embedding in embeddings]
            elapsed = time.time() - start_time
            print(f"Completed\n\nTime: {elapsed:.1f}s\n")
            return result_list

        # 2. Gemini API Fallback
        if model_ref == "gemini":
            import google.generativeai as genai
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable is missing for Gemini embeddings.")
            genai.configure(api_key=api_key)
            result = genai.embed_content(
                model="models/embedding-001",
                content=texts,
                task_type="retrieval_document"
            )
            result_list = result['embedding']
            elapsed = time.time() - start_time
            print(f"Completed\n\nTime: {elapsed:.1f}s\n")
            return result_list

        # 3. OpenAI API Fallback
        if model_ref == "openai":
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is missing for OpenAI embeddings.")
            client = OpenAI(api_key=api_key)
            response = client.embeddings.create(
                input=texts,
                model="text-embedding-ada-002"
            )
            result_list = [item.embedding for item in response.data]
            elapsed = time.time() - start_time
            print(f"Completed\n\nTime: {elapsed:.1f}s\n")
            return result_list

        raise ValueError(f"Unknown or unsupported embedding provider configured: {model_ref}")
