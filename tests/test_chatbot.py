import unittest
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from llm.chatbot import ConversationalChatbot

class TestConversationalChatbot(unittest.TestCase):
    def setUp(self):
        self.chatbot = ConversationalChatbot(provider="mock")

    def test_mock_streaming_yields_tokens(self):
        messages = [{"role": "user", "content": "How do I run the python code wrapper?"}]
        stream_tokens = list(self.chatbot.stream_chat(messages))
        
        self.assertGreater(len(stream_tokens), 0)
        full_text = "".join(stream_tokens)
        self.assertIn("wrapper", full_text.lower())
        self.assertIn("```python", full_text)

    def test_empty_messages_yields_greeting(self):
        stream_tokens = list(self.chatbot.stream_chat([]))
        full_text = "".join(stream_tokens)
        self.assertIn("Hello!", full_text)

if __name__ == "__main__":
    unittest.main()
