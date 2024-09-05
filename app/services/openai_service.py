from typing import List, AsyncGenerator

import openai
import structlog

from app.models.message import BaseChatMessage
from app.settings import settings
from app.services.llm_service import LLMServiceBase

logger = structlog.get_logger(__name__)


class AsyncOpenAIService(LLMServiceBase):
    def __init__(self):
        self.client = openai.AsyncClient(api_key=settings.llm_api_key)
        self.base_url = "https://api.openai.com/v1"
        self.model = settings.llm_model

    async def generate_stream(self, messages: List[BaseChatMessage], **kwargs) -> AsyncGenerator[str, None]:
        response_gen = await self.client.chat.completions.create(
            model=self.model,
            messages=[m.model_dump() for m in messages],
            stream=True,
            n=1,
            **kwargs
        )
        async for response in response_gen:
            if not response.choices:
                continue
            completion_delta = response.choices[0].delta.content
            if completion_delta:
                yield completion_delta

    async def generate(self, messages: List[BaseChatMessage], **kwargs) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[m.model_dump() for m in messages],
            n=1,
            **kwargs
        )
        return response.choices[0].message.content
