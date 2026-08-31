import os
import time
import logging
from typing import List, Dict, Any, Optional, Generator

logger = logging.getLogger("smart_devtool.chatbot")

class ConversationalChatbot:
    """
    Interfaces with LLM providers (Gemini, OpenAI, Groq) or mock engine to handle 
    multi-turn chat completions and stream text responses token by token.
    """
    def __init__(self, provider: Optional[str] = None, model_name: Optional[str] = None):
        self.provider = (provider or os.getenv("LLM_PROVIDER", "gemini")).lower()
        self.model_name = model_name

        if not self.model_name:
            if self.provider == "openai":
                self.model_name = os.getenv("OPENAI_MODEL", "gpt-4-turbo")
            elif self.provider == "groq":
                self.model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
            elif self.provider == "gemini":
                self.model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            else:
                self.model_name = "mock"

    def stream_chat(
        self, 
        messages: List[Dict[str, str]], 
        crawl_id: Optional[str] = None
    ) -> Generator[str, None, None]:
        """
        Yields text tokens in real time for a given conversation history.
        """
        if not messages:
            yield "Hello! How can I assist you with API development or code wrappers today?"
            return

        api_key_gemini = os.getenv("GEMINI_API_KEY")
        api_key_openai = os.getenv("OPENAI_API_KEY")
        api_key_groq = os.getenv("GROQ_API_KEY")

        # 0. Retrieve RAG documentation context if crawl_id is provided
        context = ""
        if crawl_id and self.provider != "mock":
            last_user_msg = messages[-1]["content"] if messages else ""
            if last_user_msg:
                try:
                    from rag.embeddings import EmbeddingClient
                    from rag.retriever import VectorStoreManager
                    
                    embedder = EmbeddingClient()
                    query_vector = embedder.get_embeddings([last_user_msg])[0]
                    
                    retriever = VectorStoreManager()
                    matched_chunks = retriever.query_similarity(
                        collection_name=crawl_id,
                        query_embedding=query_vector,
                        top_k=3
                    )
                    if matched_chunks:
                        context = "\n---\n".join([c["text"] for c in matched_chunks])
                        logger.info(f"Retrieved {len(matched_chunks)} chunks for chat context.")
                except Exception as e:
                    logger.error(f"RAG context retrieval failed for chatbot: {e}")

        # System prompt instruction
        system_prompt = (
            "You are Smart DevTool AI, an expert software developer and API specialist. "
            "Help developers design, debug, integrate, and understand APIs, REST patterns, and client SDK wrappers. "
            "Provide clear, concise explanations and code blocks when helpful."
        )
        if context:
            system_prompt += (
                "\n\nHere is the relevant API documentation context retrieved from the database:\n"
                f"{context}\n"
                "\nUse the above context to answer the user's questions accurately. "
                "If the answer cannot be found in the documentation context, rely on your general knowledge "
                "but make sure to mention that it is not explicitly documented."
            )

        # 1. Gemini Provider
        if self.provider == "gemini":
            if not api_key_gemini:
                logger.warning("GEMINI_API_KEY not found. Falling back to mock streaming response.")
                yield from self._stream_mock_response(messages)
                return
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key_gemini)
                model = genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=system_prompt
                )
                
                # Format history for Gemini API
                formatted_contents = []
                for msg in messages:
                    role = "user" if msg["role"] == "user" else "model"
                    formatted_contents.append({"role": role, "parts": [msg["content"]]})
                
                response = model.generate_content(formatted_contents, stream=True)
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
            except Exception as e:
                logger.error(f"Gemini streaming error: {e}")
                yield f"\n[System Error: Gemini streaming failed - {str(e)}]\n"

        # 2. OpenAI Provider
        elif self.provider == "openai":
            if not api_key_openai:
                logger.warning("OPENAI_API_KEY not found. Falling back to mock streaming response.")
                yield from self._stream_mock_response(messages)
                return
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key_openai)
                formatted_messages = [{"role": "system", "content": system_prompt}] + messages
                
                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=formatted_messages,
                    stream=True,
                    temperature=0.7
                )
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            except Exception as e:
                logger.error(f"OpenAI streaming error: {e}")
                yield f"\n[System Error: OpenAI streaming failed - {str(e)}]\n"

        # 3. Groq Provider
        elif self.provider == "groq":
            if not api_key_groq:
                logger.warning("GROQ_API_KEY not found. Falling back to mock streaming response.")
                yield from self._stream_mock_response(messages)
                return
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key_groq, base_url="https://api.groq.com/openai/v1")
                formatted_messages = [{"role": "system", "content": system_prompt}] + messages
                
                try:
                    response = client.chat.completions.create(
                        model=self.model_name,
                        messages=formatted_messages,
                        stream=True,
                        temperature=0.7
                    )
                    for chunk in response:
                        if chunk.choices and chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content
                except Exception as stream_err:
                    if "429" in str(stream_err) or "rate_limit" in str(stream_err).lower():
                        logger.warning("Groq rate limit hit. Falling back to llama-3.1-8b-instant for chatbot streaming...")
                        response = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=formatted_messages,
                            stream=True,
                            temperature=0.7
                        )
                        for chunk in response:
                            if chunk.choices and chunk.choices[0].delta.content:
                                yield chunk.choices[0].delta.content
                    else:
                        raise stream_err
            except Exception as e:
                logger.error(f"Groq streaming error ({e}). Using mock stream response.")
                yield from self._stream_mock_response(messages)

        # 4. Mock / Fallback Mode
        else:
            yield from self._stream_mock_response(messages)

    def _stream_mock_response(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        """
        Generates simulated real-time streaming response for offline testing or demonstration.
        """
        last_user_msg = messages[-1]["content"] if messages else ""
        
        if "wrapper" in last_user_msg.lower() or "code" in last_user_msg.lower():
            reply = (
                "Here is how you can use the generated wrapper code in Python:\n\n"
                "```python\n"
                "from api_client import APIClient\n\n"
                "client = APIClient(api_key='your_api_key_here')\n"
                "response = client.get_users()\n"
                "print(response)\n"
                "```\n\n"
                "This wrapper manages standard authentication headers and handles error retries automatically."
            )
        elif "authentication" in last_user_msg.lower() or "auth" in last_user_msg.lower():
            reply = (
                "API authentication typically relies on **Bearer tokens** or API keys passed in request headers. "
                "For example:\n`Authorization: Bearer <YOUR_TOKEN>`\n\n"
                "Always store API credentials securely in environment variables rather than hardcoding them."
            )
        else:
            reply = (
                f"I received your query regarding: *\"{last_user_msg}\"*\n\n"
                "As your Smart DevTool assistant, I can help extract API definitions, inspect parameters, "
                "or customize integration wrappers for Python, JavaScript, and Go. Let me know what you'd like to build!"
            )

        # Break into words/tokens with small delay to simulate real network stream
        words = reply.split(" ")
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            time.sleep(0.03)
