import httpx
import structlog

from app.models.lemonsqueezy.subscription import SubscriptionResponse, SubscriptionMultiResponse
from app.models.tier import Tier
from app.repository.users_repository import UsersRepository
from app.services.db.supabase import SupabaseConnectionService
from app.services.lemon_squeezy_service import LemonSqueezyService


logger = structlog.get_logger(__name__)


async def check_existing_subscription(user_id: str, user_email: str):
    logger.info("")
    ls_api_service = LemonSqueezyService()
    users_repository = UsersRepository(
        await SupabaseConnectionService().connect()
    )
    async with ls_api_service.get_http_client() as client:
        customer = await ls_api_service.get_customer_by_email(user_email, client)
        if not customer:
            return None

        if not customer.relationships.subscriptions.links:
            return None

        try:
            subscription_response = await client.get(customer.relationships.subscriptions.links.related)
            subscription_response.raise_for_status()
            data = subscription_response.json()
            subscriptions = SubscriptionMultiResponse(
                **data
            ) if data else None
        except httpx.HTTPStatusError as e:
            logger.warning("Failed to get subscription", user_email=user_email, status_code=e.response.status_code)

        for subscription in subscriptions.data:
            if subscription.attributes.status in ls_api_service.subscription_active_states:
                await users_repository.update_user(
                    user_id=str(user_id),
                    is_premium=True,
                    premium_until=subscription.attributes.renews_at,
                    subscription_id=subscription.id,
                    lemonsqueezy_id=subscription.attributes.customer_id,
                    variant_id=subscription.attributes.variant_id,
                    tier=Tier.PREMIUM if not subscription.attributes.is_lifetime else Tier.LIFETIME
                )
                return