import asyncio
from typing import Dict, Optional, AsyncGenerator

import sentry_sdk
import structlog

from app.models.completion import RephraseTaskType, RephraseRequest
from app.models.sse import SSEEvent
from app.services.llm.anthropic_service import AnthropicService
from app.services.llm.openai_service import AsyncOpenAIService
from app.services.rewrite.actions.advanced_improve_writing_service import AdvancedImproveAction
from app.services.rewrite.actions.base import BaseRephraseAction, ActionFailed
from app.services.rewrite.actions.concise_service import ConciseAction
from app.services.rewrite.actions.improve_writing_action import ImproveWritingAction
from app.services.rewrite.actions.proofread_action import ProofreadAction
from app.services.usage.free_tier_usage.base import BaseFreeTierUsageService
from app.settings import LLMProvider, settings

logger = structlog.get_logger(__name__)


class UnsupportedRewriteAction(Exception):
    pass


class RewriteManager:
    llm_service = AsyncOpenAIService() if settings.llm_provider == LLMProvider.OPENAI.value else AnthropicService()
    actions_mapping: Dict[RephraseTaskType, BaseRephraseAction] = {}

    @classmethod
    def _init_actions_mapping(cls):
        actions_mapping: Dict[RephraseTaskType, BaseRephraseAction] = {
            RephraseTaskType.FIX_GRAMMAR: ProofreadAction(
                llm_service=cls.llm_service,
            ),
            RephraseTaskType.CONCISE: ConciseAction(
                llm_service=cls.llm_service,
            ),
            RephraseTaskType.REPHRASE: AdvancedImproveAction()
        }
        return actions_mapping

    def __init__(
            self,
            usage_service: Optional[BaseFreeTierUsageService] = None,
            initial_sleep: Optional[float] = 5,
            streaming_sleep: Optional[float] = 0.5,
            sse_formatting: Optional[bool] = True
    ):
        self.usage_service = usage_service
        self._initial_sleep = initial_sleep
        self._streaming_sleep = streaming_sleep
        self._sse_formatting = sse_formatting
        if not self.actions_mapping:
            self.actions_mapping = self._init_actions_mapping()

    @staticmethod
    def _sse_end_of_stream():
        return {
            "data": "end of stream",
            "event": SSEEvent.EOS.value
        }

    def _format_content(self, event: SSEEvent | str, content: str):
        if self._sse_formatting:
            return {
                "data": content,
                "event": event.value if isinstance(event, SSEEvent) else event
            }
        return content

    @staticmethod
    def _sse_throttle():
        return {
            "data": "throttle",
            "event": SSEEvent.THROTTLE.value
        }

    async def rewrite(self, rephrase_request: RephraseRequest) -> AsyncGenerator[str, None]:
        logger.info("Rewriting", task_type=rephrase_request.completion_task_type)
        if self.usage_service:
            try:
                is_user_allowed = await self.usage_service.is_user_allowed(user_id=rephrase_request.uid)
            except Exception as e:
                logger.error("Usage service failed", error=str(e))
                sentry_sdk.capture_exception(e)
                is_user_allowed = True
        else:
            is_user_allowed = True

        if not is_user_allowed:
            logger.debug("User not allowed", user_id=rephrase_request.uid)
            yield self._sse_throttle()
            await asyncio.sleep(self._initial_sleep)

        action = self.actions_mapping.get(rephrase_request.completion_task_type)
        if not action:
            raise UnsupportedRewriteAction(
                f"Unsupported task type {rephrase_request.completion_task_type}"
            )

        try:
            async for event, sse_chunk in action.perform(rephrase_request.text, prev_rewrites=rephrase_request.prev_rewrites):
                yield self._format_content(event, sse_chunk)
                if not is_user_allowed:
                    await asyncio.sleep(self._streaming_sleep)
        except ActionFailed as e:
            sentry_sdk.capture_exception(e)
            logger.error("Action failed", error=str(e))
            if e.type == RephraseTaskType.REPHRASE:
                fallback_action = ImproveWritingAction(
                    llm_service=self.llm_service
                )
                async for event, sse_chunk in fallback_action.perform(rephrase_request.text, prev_rewrites=rephrase_request.prev_rewrites):
                    yield self._format_content(event, sse_chunk)
            else:
                yield self._format_content(SSEEvent.ERROR, str(e))

        if self._sse_formatting:
            yield self._sse_end_of_stream()
