from abc import ABC, abstractmethod
from typing import Any, Optional

from langchain.chat_models.base import BaseChatModel


class BaseChatClient(ABC):

    @abstractmethod
    def get_client(self, model: Optional[str] = None, **kwargs: Any) -> BaseChatModel:
        pass