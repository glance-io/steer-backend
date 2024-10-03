from datetime import datetime

import httpx
import sentry_sdk
import structlog
from postgrest.types import CountMethod
from supabase import AsyncClient

from app.models.lemonsqueezy.license import LicenseResponse
from app.models.lemonsqueezy.subscription import SubscriptionResponse, SubscriptionAttributes, SubscriptionData
from app.settings import settings

logger = structlog.getLogger(__name__)


class LicenseNotActiveException(Exception):
    pass


class LemonSqueezyService:
    api_url = "https://api.lemonsqueezy.com/v1"

    def __init__(self, db: AsyncClient):
        self.db = db

    # noinspection DuplicatedCode
    async def __get_subscription_item_from_order_product(self, order_item_id: int, client: httpx.AsyncClient) -> int:
        response = await client.get(
            f"{self.api_url}/subscriptions",
            params={"filter[order_item_id]": str(order_item_id)}
        )
        response.raise_for_status()
        data = response.json().get('data', [])
        if not len(data) == 1:
            raise ValueError(f"Expected 1 subscription item, got {len(data)}")
        subscription_id = data[0].get('id')
        if not subscription_id:
            raise ValueError("Could not obtain subscription id from order item")
        return subscription_id

    async def validate_license(self, license_key: str, instance_id: str, client: httpx.AsyncClient):
        response = await client.post(
            f"{self.api_url}/licenses/validate",
            json={
                "license_key": license_key,
                "instance_id": instance_id
            }
        )
        response.raise_for_status()
        data = response.json()
        ls_license = LicenseResponse(**data)
        if ls_license.error:
            raise ValueError(ls_license.error)
        return ls_license

    async def get_subscription_detail(self, subscription_id: int, client: httpx.AsyncClient) -> SubscriptionData:
        response = await client.get(
            f"{self.api_url}/subscriptions/{subscription_id}"
        )
        response.raise_for_status()
        subscription_response = SubscriptionResponse(**response.json())
        return subscription_response.data

    async def process_and_store_subscription(
            self,
            user_id: str,
            license_key: str,
            instance_id: str,
            subscription_detail: SubscriptionData
    ) -> bool:
        # FIXME: This method also handles user creation, which should be moved to a separate service
        active_states = {'on_trial', 'active', 'paused', 'past_due'}
        is_active = subscription_detail.attributes.status in active_states

        # Update user
        upsert_resp = await self.db.table("users").upsert({
            "id": user_id,
            "is_premium": is_active,
            "license_key": license_key,
            "subscription_id": subscription_detail.id,
            "instance_id": instance_id
        }, count=CountMethod.exact).execute()
        if not upsert_resp.count:
            raise ValueError("Failed to update user subscription")

        # Update subscription
        if is_active:
            await self.db.table("subscription_payments").upsert({
                "user_id": user_id,
                "valid_from": datetime.now().isoformat(),   # technically not true, but works for our purposes
                "valid_until": subscription_detail.attributes.renews_at.isoformat(),
            }, count=CountMethod.exact).execute()
        return is_active

    async def pair_existing_license_with_user(self, user_id: str, license_key: str, instance_id: str):
        # Get subscription id

        # Get subscription status + payment
        # Persist into db
        # Profit?
        try:
            async with httpx.AsyncClient(
                    headers={"Authorization": f"Bearer {settings.lemonsqueezy_api_key}"}
            ) as client:
                ls_license = await self.validate_license(license_key, instance_id, client)
                if not ls_license.valid or not ls_license.license_key.status == 'active':
                    logger.info(
                        "Submitted inactive license", user_id=user_id, license_key=license_key, instance_id=instance_id
                    )
                    return False
                subscription_item_id = await self.__get_subscription_item_from_order_product(
                    ls_license.meta.order_item_id, client
                )
                subscription_detail = await self.get_subscription_detail(subscription_item_id, client)
                is_active = await self.process_and_store_subscription(
                    user_id, license_key, instance_id, subscription_detail
                )
                return is_active
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP status Error Lemon Squeezy: {e}")
            sentry_sdk.capture_exception(e)
            raise ValueError(f"Failed to validate license: {e}")
