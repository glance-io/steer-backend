import asyncio
from typing import Optional, AsyncGenerator

import structlog
from app.models.completion import RephraseTaskType, RephraseRequest
from app.models.message import SystemMessage, UserMessage, AssistantMessage
from app.services.llm_service import LLMServiceBase
from app.services.prompt_service import PromptService
from app.services.usage.free_tier_usage.base import BaseFreeTierUsageService
from app.services.usage.token_based.lemonsqueezy import LemonSqueezyUsageService
from app.services.usage.token_based.mixpannel import MixpanelUsageService
from app.settings import settings

logger = structlog.get_logger(__name__)


class RewriteService:
    prompt_service = PromptService()

    def __init__(
            self,
            rewrite_request: RephraseRequest,
            llm_service: LLMServiceBase,
            usage_service: BaseFreeTierUsageService
    ):
        self.rewrite_request = rewrite_request
        self.llm_service = llm_service
        self.usage_service = usage_service

    @staticmethod
    def _format_token(token, use_sse: bool):
        if use_sse:
            return {
                "data": token,
                "event": "data"
            }
        return token

    @staticmethod
    def _sse_end_of_stream():
        return {
            "data": "end of stream",
            "event": "eos"
        }

    @staticmethod
    def _sse_throttle():
        return {
            "data": "throttle",
            "event": "throttle"
        }

    @staticmethod
    def __get_temperature(task_type: RephraseTaskType):
        return settings.fix_grammar_temperature \
            if task_type == RephraseTaskType.FIX_GRAMMAR\
            else settings.rephrase_temperature

    async def rewrite(self, sse_formating: Optional[bool] = True) -> AsyncGenerator[str, None]:
        logger.info("Rewriting started", task=self.rewrite_request.completion_task_type)
        prompt = self.prompt_service.get_prompt(
            self.rewrite_request.completion_task_type,
            len(self.rewrite_request.text.split(" ")) == 1,
            self.rewrite_request.prev_rewrites,
            self.rewrite_request.app_name
        )
        conversation_messages = [
            SystemMessage(content=prompt),
            UserMessage(content=self.rewrite_request.text)
        ]
        is_user_allowed = await self.usage_service.is_user_allowed(
            user_id=self.rewrite_request.uid,
        )
        if not is_user_allowed:
            yield self._sse_throttle()
            await asyncio.sleep(5)

        response_generator = self.llm_service.generate_stream(
            messages=conversation_messages,
            temperature=self.__get_temperature(self.rewrite_request.completion_task_type)
        )
        rewrite = ""
        async for response_delta in response_generator:

            if response_delta:
                rewrite += response_delta
                yield self._format_token(response_delta, sse_formating)
        if sse_formating:
            yield self._sse_end_of_stream()
            logger.debug('sse eos')

        logger.info("Rewrite completed", rewrite=rewrite, original_text=self.rewrite_request.text)
        conversation_messages.append(AssistantMessage(content=rewrite))
        await asyncio.create_task(self.usage_service.update_user_usage(
            user_id=self.rewrite_request.uid,
            usage_delta=1
        ))
