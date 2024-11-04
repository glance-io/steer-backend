import abc
from typing import AsyncGenerator, List, Optional, Tuple

import sentry_sdk
import structlog

from app.models.completion import RephraseTaskType
from app.models.sse import SSEEvent
from app.services.prompt_service import PromptService

logger = structlog.get_logger(__name__)


class BaseRephraseAction(abc.ABC):
    base_temperature: float
    max_rewrite_temp: float
    task_type: RephraseTaskType

    _prompt_service = PromptService()

    @abc.abstractmethod
    async def _perform(
            self,
            original_message: str,
            prev_rewrites: List[str] | None,
            application: Optional[str] = None
    ) -> AsyncGenerator[Tuple[SSEEvent, str], None]:
        raise NotImplementedError()

    async def perform(
            self,
            original_message: str,
            prev_rewrites: List[str] | None,
            application: Optional[str] = None
    ) -> AsyncGenerator[Tuple[SSEEvent, str], None]:
        try:
            async for event, content in self._perform(original_message, prev_rewrites):
                yield event, content
        except Exception as e:
            sentry_sdk.capture_exception(e)
            logger.error("Action failed", error=str(e))
