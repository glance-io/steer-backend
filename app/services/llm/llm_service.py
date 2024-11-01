from abc import ABC, abstractmethod
from typing import AsyncGenerator, List, Dict
from app.models.message import BaseChatMessage

class LLMServiceBase(ABC):
    @abstractmethod
    async def generate_stream(self, messages: List[BaseChatMessage], **kwargs) -> AsyncGenerator[str, None]:
        pass

    @abstractmethod
    async def generate(self, messages: List[BaseChatMessage], **kwargs) -> str:
        pass