from typing import List

import httpx

from app.models.message import BaseChatMessage
from app.models.usage import CurrentUsage
from app.services.usage.token_based.base import BaseUsageService, logger
from app.settings import settings


class LemonSqueezyUsageService(BaseUsageService):
    api_url = "https://api.lemonsqueezy.com/v1"

    @property
    def client(self):
        return httpx.AsyncClient(
            headers={"Authorization": f"Bearer {settings.lemonsqueezy_api_key}"}
        )

    async def __get_subscription_item_from_order_product(self, order_item_id: str, client: httpx.AsyncClient):
        response = await client.get(
            f"{self.api_url}/subscriptions",
            params={"filter[order_item_id]": order_item_id}
        )
        response.raise_for_status()
        data = response.json().get('data', [])
        if not len(data) == 1:
            raise ValueError(f"Expected 1 subscription item, got {len(data)}")
        return data[0].get('attributes', {}).get('first_subscription_item', {}).get('id')

    async def update_user_usage(self, messages: List[BaseChatMessage]):
        token_count = self.get_conversation_tokens(messages)
        async with self.client as client:
            subscription_item_id = await self.__get_subscription_item_from_order_product(self.uid, client)
            response = await client.post(
                f"{self.api_url}/usage-records",
                json={
                    "data": {
                        "type": "usage-records",
                        "attributes": {
                            "quantity": token_count
                        },
                        "relationships": {
                            "subscription-item" : {
                                "data": {
                                    "type": "subscription-items",
                                    "id": str(subscription_item_id)
                                }
                            }
                        }
                    }
                }
            )
            response.raise_for_status()
            logger.info("Updated user usage", subscription_item_id=subscription_item_id, usage_delta=token_count)

    async def get_user_usage(self) -> CurrentUsage:
        async with self.client as client:
            subscription_item_id = await self.__get_subscription_item_from_order_product(self.uid, client)
            response = await client.get(f"{self.api_url}/subscription-items/{subscription_item_id}/current-usage")
            response.raise_for_status()
            return CurrentUsage(**response.json()['meta']   )
