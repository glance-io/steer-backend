from typing import List

import structlog
import tiktoken

from app.models.message import BaseChatMessage
from app.settings import settings

logger = structlog.get_logger(__name__)


class BaseUsageService:
    model = settings.llm_model

    def __init__(self, uid: str):
        self.uid = uid

    def get_token_count(self, text: str) -> int:
        encoding = tiktoken.encoding_for_model(self.model)
        return len(encoding.encode(text))

    def get_conversation_tokens(self, messages: List[BaseChatMessage]):
        return sum([self.get_token_count(message.content) for message in messages])

    async def update_user_usage(self, messages: List[BaseChatMessage]):
        logger.info("Updating user usage", uid=self.uid, usage_delta=self.get_conversation_tokens(messages))

    async def get_user_usage(self):
        logger.info("Getting user usage", uid=self.uid)