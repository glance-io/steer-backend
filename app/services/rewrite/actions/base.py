import abc
from typing import AsyncGenerator, List, Optional, Tuple

import sentry_sdk
import structlog

from app.models.completion import RephraseTaskType
from app.models.sse import SSEEvent

logger = structlog.get_logger(__name__)


class ActionFailed(Exception):
    def __init__(self, type: RephraseTaskType, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type = type


class BaseRephraseAction(abc.ABC):
    base_temperature: float
    max_rewrite_temp: float
    task_type: RephraseTaskType

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
            raise ActionFailed(self.task_type, str(e))
