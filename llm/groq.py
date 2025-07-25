import os
from typing import Any

from langchain_groq import ChatGroq
from llm.base import BaseChatClient


class GroqChatClient(BaseChatClient):
    
    def get_client(self, model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"), **kwargs: Any) -> ChatGroq:
        return ChatGroq(model=model, **kwargs)