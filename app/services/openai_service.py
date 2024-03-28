from typing import List, AsyncGenerator

import openai
import structlog

from app.models.message import BaseChatMessage
from app.settings import settings

logger = structlog.get_logger(__name__)


class AsyncOpenAIService:
    def __init__(self):
        self.client = openai.AsyncClient(api_key=settings.openai_api_key)
        self.base_url = "https://api.openai.com/v1"
        self.model  = settings.openai_model

    async def stream_completions(self, messages: List[BaseChatMessage], **kwargs) -> AsyncGenerator[str, None]:
        response_gen = await self.client.chat.completions.create(
            model=self.model,
            messages=[m.dict() for m in messages],
            stream=True,
            n=1,
            **kwargs
        )
        async for response in response_gen:
            if not response.choices:
                continue
            completion_delta = response.choices[0].delta.content
            yield completion_delta
