from typing import List, AsyncGenerator
from anthropic import AsyncAnthropic
import structlog
from app.models.message import BaseChatMessage, SystemMessage
from app.settings import settings
from .llm_service import LLMServiceBase

logger = structlog.get_logger(__name__)

class AnthropicService(LLMServiceBase):
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.llm_api_key)

    def _prepare_messages(self, messages: List[BaseChatMessage]):
        system_message = next((m for m in messages if isinstance(m, SystemMessage)), None)
        other_messages = [m for m in messages if not isinstance(m, SystemMessage)]
        
        return {
            "system": system_message.content if system_message else None,
            "messages": [{"role": m.role, "content": m.content} for m in other_messages]
        }

    async def generate_stream(self, messages: List[BaseChatMessage], **kwargs) -> AsyncGenerator[str, None]:
        prepared_messages = self._prepare_messages(messages)
        stream = await self.client.messages.create(
            model=settings.llm_model,
            **prepared_messages,
            max_tokens=1024,
            stream=True,
            **kwargs
        )
        async for event in stream:
            if event.type == "content_block_start":
                continue
            elif event.type == "content_block_delta":
                yield event.delta.text
            elif event.type == "message_stop":
                break

    async def generate(self, messages: List[BaseChatMessage], **kwargs) -> str:
        prepared_messages = self._prepare_messages(messages)
        response = await self.client.messages.create(
            model=settings.llm_model,
            **prepared_messages,
            max_tokens=1024,
            **kwargs
        )
        return response.content[0].text