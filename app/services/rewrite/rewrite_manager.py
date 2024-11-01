import asyncio
from typing import Dict, Optional, AsyncGenerator

import sentry_sdk
import structlog

from app.models.completion import RephraseTaskType, RephraseRequest
from app.services.rewrite.actions.base import BaseRephraseAction
from app.services.usage.free_tier_usage.base import BaseFreeTierUsageService

logger = structlog.get_logger(__name__)


class UnsupportedRewriteAction(Exception):
    pass


class RewriteManager:
    actions_mapping: Dict[RephraseTaskType, BaseRephraseAction] = {}

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

    def _format_token(self, token):
        if self._sse_formatting:
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

        async for token in action.perform(rephrase_request):
            yield self._format_token(token)
            await asyncio.sleep(self._streaming_sleep)

        if self._sse_formatting:
            yield self._sse_end_of_stream()
