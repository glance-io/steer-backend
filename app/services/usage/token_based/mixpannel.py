from typing import List

import structlog

from app.models.message import BaseChatMessage
from app.services.usage.token_based.base import BaseUsageService
from mixpanel import Mixpanel
from app.settings import settings

logger = structlog.get_logger(__name__)


class MixpanelUsageService(BaseUsageService):
    def __init__(self, uid: str):
        super().__init__(uid)
        self.mixpanel_client = Mixpanel(
            settings.mixpanel_api_key
        )

    async def get_user_usage(self):
        raise NotImplemented(
            "usage can be obtained in Mixpanel"
        )

    async def update_user_usage(self, messages: List[BaseChatMessage]):
        token_usage = self.get_conversation_tokens(messages)
        self.mixpanel_client.track(
            self.uid,
            "token-usage",
            {
                "usage_delta": token_usage
            }
        )
        logger.info("Updated user token usage", uid=self.uid, usage_delta=token_usage)