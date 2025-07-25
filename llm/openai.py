import os
from typing import Any

from langchain.chat_models import ChatOpenAI
from llm.base import BaseChatClient


class OpenAIChatClient(BaseChatClient):
    
    def get_client(self, model=os.getenv("GPT_MODEL"), **kwargs: Any) -> ChatOpenAI:
        return ChatOpenAI(model=model, **kwargs)