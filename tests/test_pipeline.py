import os
import unittest
import sys
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Adjust path to import local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parser.cleaner import HTMLCleaner, clean_html, extract_api_sections
from rag.chunker import MarkdownChunker
from rag.embeddings import EmbeddingClient
from rag.retriever import VectorStoreManager
from llm.extractor import APIExtractor
from generator.wrapper_generator import WrapperGenerator

class TestSmartDevtoolPipeline(unittest.TestCase):
    
    def setUp(self):
        self.mock_html = """
        <html>
            <head><title>Test API Reference Documentation</title></head>
            <body>
                <nav>
                    <a href="/home">Home</a>
                </nav>
                <div id="content">
                    <h1>Test API v1</h1>
                    <p>Welcome to the Test API documentation. The base URL is <code>https://api.test.com/v1</code>.</p>
                    
                    <h2>Authentication</h2>
                    <p>Authenticate by passing the API key in the Authorization header. Example: <code>Authorization: Bearer TEST_API_KEY</code></p>
                    
                    <h2>Create User</h2>
                    <p>To create a new user, issue a POST request to the <code>/users</code> path.</p>
                    
                    <h3>Parameters</h3>
                    <table>
                        <tr>
                            <th>Parameter</th>
                            <th>Type</th>
                            <th>Required</th>
                            <th>Description</th>
                        </tr>
                        <tr>
                            <td>username</td>
                            <td>string</td>
                            <td>true</td>
                            <td>The unique user account username.</td>
                        </tr>
                        <tr>
                            <td>email</td>
                            <td>string</td>
                            <td>false</td>
                            <td>Email address associated with the user account.</td>
                        </tr>
                    </table>
                </div>
                <footer>
                    <p>&copy; 2026 Test Inc.</p>
                </footer>
            </body>
        </html>
        """
        self.cleaner = HTMLCleaner()
        self.chunker = MarkdownChunker(chunk_size=1000, chunk_overlap=100)
        self.embeddings = EmbeddingClient()
        self.retriever = VectorStoreManager(persist_directory="./data/test_chroma")
        self.extractor = APIExtractor(provider="mock")
        self.generator = WrapperGenerator()

    def tearDown(self):
        # Delete test database files after run
        self.retriever.delete_collection("test_pipeline_coll")

    def test_pipeline_execution(self):
        print("\n=== STARTING PIPELINE INTEGRATION TEST ===")

        # 1. Test HTML Cleaning
        print("[1/6] Running HTMLCleaner...")
        cleaned_md = self.cleaner.clean(self.mock_html)
        self.assertIn("# Test API v1", cleaned_md)
        self.assertIn("## Authentication", cleaned_md)
        self.assertIn("## Create User", cleaned_md)
        self.assertIn("| username | string | true | The unique user account username. |", cleaned_md)
        # Verify boilerplate tags were removed
        self.assertNotIn("Home", cleaned_md) # from nav
        self.assertNotIn("2026 Test Inc.", cleaned_md) # from footer
        print(" -> HTML cleaning passed.")

        # 2. Test Chunker
        print("[2/6] Running Chunker...")
        chunks = self.chunker.split(cleaned_md)
        self.assertGreater(len(chunks), 0)
        for c in chunks:
            self.assertTrue(c["text"].startswith("Context:"))
            self.assertIn("headers", c["metadata"])
        print(f" -> Chunker split into {len(chunks)} sections.")

        # 3. Test Embeddings
        print("[3/6] Running Embeddings...")
        texts = [c["text"] for c in chunks]
        vectors = self.embeddings.get_embeddings(texts)
        self.assertEqual(len(vectors), len(chunks))
        self.assertEqual(len(vectors[0]), self.embeddings.dimension)
        print(" -> Vector embedding generation passed.")

        # 4. Test ChromaDB Retriever
        print("[4/6] Running VectorStoreManager (ChromaDB)...")
        collection_name = "test_pipeline_coll"
        self.retriever.add_documents(collection_name, chunks, vectors)
        
        # Test Query
        query_text = "how to authenticate or create users"
        query_vector = self.embeddings.get_embeddings([query_text])[0]
        results = self.retriever.query_similarity(collection_name, query_vector, top_k=2)
        
        self.assertGreater(len(results), 0)
        self.assertIn("chunk_id", results[0])
        self.assertIn("text", results[0])
        self.assertGreater(results[0]["score"], 0.0)
        print(f" -> Vector query search returned top match ID: {results[0]['chunk_id']} (score={results[0]['score']})")

        # 5. Test API Extractor
        print("[5/6] Running LLM Schema Extractor...")
        context_texts = [r["text"] for r in results]
        schema = self.extractor.extract(context_texts, "Create a user account")
        
        self.assertEqual(schema["api_name"], "Target API")
        self.assertIn("base_url", schema)
        self.assertEqual(schema["authentication"]["type"], "bearer")
        self.assertEqual(schema["endpoints"][0]["path"], "/users")
        self.assertEqual(schema["endpoints"][0]["method"], "POST")
        print(" -> Schema extractor parameters parsed.")

        # 6. Test Wrapper Generator rendering
        print("[6/6] Running Wrapper Generator templates rendering...")
        python_code = self.generator.render(schema, "python")
        self.assertIn("class TargetApiClient:", python_code)
        self.assertIn("def create_user", python_code) # fallback generated method
        self.assertIn("Authorization", python_code)
        
        js_code = self.generator.render(schema, "javascript")
        self.assertIn("class TargetApiClient", js_code)
        self.assertIn("module.exports = TargetApiClient;", js_code)
        print(" -> Code client wrappers rendering passed.")
        print("=== PIPELINE INTEGRATION TEST COMPLETED SUCCESSFULLY ===\n")

if __name__ == "__main__":
    unittest.main()
