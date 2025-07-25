import os
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from llm.base import BaseChatClient



class GeminiChatClient(BaseChatClient):
    
    def get_client(self, model=os.getenv("GEMINI_MODEL","gemini-1.5-flash"), **kwargs: Any) -> ChatGoogleGenerativeAI:
        try:
            print(model)
            return ChatGoogleGenerativeAI(model=model, **kwargs)
        except Exception as e:
            print(e)
            return None
