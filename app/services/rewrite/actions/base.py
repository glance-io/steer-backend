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

    @staticmethod
    def _get_locale_mapping(locale: str) -> str:
        """Map locale codes to our supported English variants"""
        
        # Australian English group
        australian_locales = {'en_AU', 'en_NZ', 'en_FJ', 'en_PG', 'en_SB', 'en_VU', 'en_TO', 'en_WS', 'en_CK'}
        
        # British English group  
        british_locales = {'en_GB', 'en_SG', 'en_MY', 'en_HK', 'en_IE', 'en_MT', 'en_CY', 'en_ZA', 'en_ZW', 'en_BW', 'en_NA', 
                          'en_SZ', 'en_LS', 'en_MW', 'en_ZM', 'en_UG', 'en_KE', 'en_TZ', 'en_GH', 
                          'en_NG', 'en_SL', 'en_GM', 'en_BZ', 'en_GY', 'en_TT', 'en_JM', 
                          'en_BB', 'en_BS', 'en_AG', 'en_DM', 'en_GD', 'en_KN', 'en_LC', 'en_VC'}
        
        if locale in australian_locales:
            return 'en_AU'
        elif locale in british_locales:
            return 'en_GB'
        else:
            return 'en_US'  # Default fallback

    @abc.abstractmethod
    async def _perform(
            self,
            original_message: str,
            prev_rewrites: List[str] | None,
            application: Optional[str] = None,
            locale: Optional[str] = None
    ) -> AsyncGenerator[Tuple[SSEEvent, str], None]:
        raise NotImplementedError()

    async def perform(
            self,
            original_message: str,
            prev_rewrites: List[str] | None,
            application: Optional[str] = None,
            locale: Optional[str] = None
    ) -> AsyncGenerator[Tuple[SSEEvent, str], None]:
        try:
            # TODO: Instead of none pass application
            async for event, content in self._perform(original_message, prev_rewrites, None, locale):
                yield event, content
        except Exception as e:
            raise ActionFailed(self.task_type, str(e))
