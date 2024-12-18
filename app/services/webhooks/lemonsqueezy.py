import asyncio
import datetime
import json
import uuid
from typing import Any, Dict, Optional

import httpx
import sentry_sdk
import structlog
from postgrest.types import CountMethod
from sentry_sdk import capture_message
from supabase import AsyncClient

from app.models.lemonsqueezy.order import Order
from app.models.lemonsqueezy.subscription import Subscription
from app.models.lemonsqueezy.subscription_invoice import SubscriptionInvoice
from app.models.lemonsqueezy.webhooks import WebhookPayload, EventType as WebhookEventType
from app.models.tier import Tier
from app.models.users import User
from app.repository.payments_repository import PaymentsRepository
from app.repository.users_repository import UsersRepository
from app.services.cache.redis_cache import RedisCacheService
from app.services.db.supabase import SupabaseConnectionService
from app.services.lemon_squeezy_service import LemonSqueezyService as LemonsqueezyAPIService
from app.services.usage.free_tier_usage.free_tier_usage_service_with_cache import FreeTierUsageServiceWithCache
from app.settings import settings

logger = structlog.getLogger(__name__)


class RawWebhookStorageError(Exception):
    pass


class LSUserNotFoundError(Exception):
    ...


class DBInconsistencyError(Exception):
    def __init__(self, uid: str, message: str = "Database inconsistency error"):
        self.uid = uid
        super().__init__(f"{message} for user {uid}")


class LemonsqueezyWebhookService:
    model = WebhookPayload
    subscription_active_states = {'on_trial', 'active', 'paused', 'past_due', 'cancelled'}

    def __init__(self, db: AsyncClient):
        self.db = db
        self.table = self.db.table("webhook_raw")
        self._users_repository = UsersRepository(db)
        self._payments_repository = PaymentsRepository(db)
        self._ls_api_service = LemonsqueezyAPIService()
        self._free_tier_usage_service = FreeTierUsageServiceWithCache(
            cache=RedisCacheService(),
            db=db,
        )

    def _validate_data(self, data: Dict[str, Any]):
        try:
            return self.model.model_validate(data)
        except Exception as e:
            logger.error("Failed to validate webhook data", data=data, error=str(e))
            sentry_sdk.capture_exception(e)
            raise e

    async def _handle_order_created(self, data: Order, user_id: str):
        variant, price = await self._ls_api_service.get_product_variant_detail(
            data.attributes.first_order_item.variant_id,
            httpx.AsyncClient(
                headers={"Authorization": f"Bearer {settings.lemonsqueezy_api_key}"}
            )
        )
        if price.attributes.is_lifetime:
            logger.debug("User purchased lifetime subscription", user_id=user_id)
            premium_until = datetime.datetime.max
            await self._users_repository.update_user(
                user_id=user_id,
                is_premium=True,
                premium_until=premium_until,
                lemonsqueezy_id=data.attributes.customer_id,
                subscription_id=None,
                variant_id=data.attributes.first_order_item.variant_id,
                tier=Tier.LIFETIME,
            )
        else:
            logger.debug("Non-lifetime subscription purchased", user_id=user_id)

    async def _handle_order_refunded(self, data: Order, user_id: str):
        user = await self._users_repository.get_user(user_id)
        if user.variant_id == data.attributes.first_order_item.variant_id:
            await self._users_repository.update_user(
                user_id=user_id,
                is_premium=False,
                premium_until=None,
                lemonsqueezy_id=data.attributes.customer_id,
                subscription_id=None,
                variant_id=None,
                tier=Tier.FREE
            )
        else:
            logger.warning(
                "User variant does not match refunded variant",
                user_id=user_id,
                user_variant_id=user.variant_id,
                refunded_variant_id=data.attributes.first_order_item.variant_id
            )
            sentry_sdk.set_context("ls_webhook", {
                'user_id': user_id,
                'user_variant_id': user.variant_id,
                'refunded_variant_id': data.attributes.first_order_item.variant_id
            })
            sentry_sdk.capture_message("User variant does not match refunded variant")
            raise DBInconsistencyError(uid=user_id)

    async def _process_order_event(self, event_type: WebhookEventType, data: Order, user_id: str | None):
        if not user_id:
            user_id = await self._get_user_id_by_lemonsqueezy_id(data.attributes.customer_id)
        logger.debug("Processing order event", event_type=event_type, data=data)
        if not data.attributes.first_order_item.product_id == settings.lemonsqueezy_product_id:
            logger.warning("Order is not for our product", product_id=data.attributes.first_order_item.product_id,
                           config_id=settings.lemonsqueezy_product_id)
            sentry_sdk.set_context("ls_webhook", {'data': data})
            sentry_sdk.capture_message("Order is not for our product")
            return
        if event_type == WebhookEventType.ORDER_CREATED:
            await self._handle_order_created(data, user_id)
        elif event_type == WebhookEventType.ORDER_REFUNDED:
            await self._handle_order_refunded(data, user_id)
        else:
            logger.warning("Unknown event type for order", event_type=event_type, data=data)
            sentry_sdk.set_context("ls_webhook", {'event_type': event_type, 'data': data})
            sentry_sdk.capture_message("Unknown event type for order")

    async def _handle_subscription_created(self, data: Subscription, user_id: str | None):
        if not user_id:
            logger.error("User ID not found in custom data", data=data)
            sentry_sdk.set_context("ls_webhook",{'data': data})
            sentry_sdk.capture_message("User ID not found in custom data")
            raise ValueError("User ID not found in custom data")
        user = await self._users_repository.update_user(
            user_id=user_id,
            is_premium=True,
            premium_until=data.attributes.renews_at.isoformat(),
            lemonsqueezy_id=data.attributes.customer_id,
            subscription_id=data.id,
            variant_id=data.attributes.variant_id,
            tier=Tier.PREMIUM
        )
        logger.info("User created subscription", user=user)

    async def _get_user_id_by_lemonsqueezy_id(self, lemonsqueezy_id: int, only_id: Optional[bool] = True) -> uuid.UUID | User:
        user = await self._users_repository.get_user_by_lemonsqueezy_id(lemonsqueezy_id)
        if not user:
            logger.error("User not found by lemonsqueezy_id", lemonsqueezy_id=lemonsqueezy_id)
            sentry_sdk.set_context('user-lemonsqueezy', {'lemonsqueezy_id': lemonsqueezy_id})
            sentry_sdk.capture_message("User not found by lemonsqueezy_id")
            raise LSUserNotFoundError("User not found by lemonsqueezy_id")
        if only_id:
            return user.id
        return user

    async def _handle_subscription_payment_success(self, data: SubscriptionInvoice, user_id: str | None):
        try:
            user = await self._users_repository.get_user(user_id) \
                if user_id \
                else await self._get_user_id_by_lemonsqueezy_id(data.attributes.customer_id, only_id=False)
            user_id = user.id
            if not user.subscription_id == data.attributes.subscription_id:
                raise DBInconsistencyError(message="User subscription_id does not match with the event data",
                                           uid=str(user_id))
            email = user.email
        except LSUserNotFoundError:
            capture_message(f"Could not find user by lemonsqueezy_id - {data.attributes.customer_id}")
            customer = await self._ls_api_service.get_customer(
                data.attributes.customer_id, self._ls_api_service.get_http_client()
            )
            email = customer.attributes.email
            user_id = None

        payment_record = await self._payments_repository.create(
            email=email,
            created_at=data.attributes.created_at,
            user_id=user_id,
            updated_at=data.attributes.updated_at,
            total=data.attributes.total,
            subtotal=data.attributes.subtotal,
            billing_reason=data.attributes.billing_reason,
            status=data.attributes.status,
            currency=data.attributes.currency,
            ls_subscription_id=data.attributes.subscription_id,
        )
        logger.info("Payment record created", payment_record=payment_record, user_id=user_id)

    async def _handle_subscription_updated(self, data: Subscription, user_id: str | None):
        if not user_id:
            user_id = str(await self._get_user_id_by_lemonsqueezy_id(data.attributes.customer_id))
        user = await self._users_repository.get_user(user_id)
        if not (user.subscription_id and  user.subscription_id == data.id and user.variant_id and user.variant_id == data.attributes.variant_id):
            raise DBInconsistencyError(message="User subscription_id or variant_id does not match with the event data", uid=user_id)
        if data.attributes.status in self.subscription_active_states:
            user = await self._users_repository.update_user(
                user_id=user_id,
                is_premium=True,
                premium_until=data.attributes.renews_at,
                lemonsqueezy_id=data.attributes.customer_id,
                subscription_id=data.id,
                variant_id=data.attributes.variant_id,
                tier=Tier.PREMIUM
            )
        else:
            user = await self._users_repository.update_user(
                user_id=user_id,
                is_premium=False,
                premium_until=None,
                lemonsqueezy_id=data.attributes.customer_id,
                subscription_id=None,
                variant_id=None,
                tier=Tier.FREE
            )
        logger.info("User updated subscription", user=user)

    async def _handle_subscription_cancelled(self, data: Subscription, user_id: str | None):
        user = await self._users_repository.get_user(user_id) \
            if user_id \
            else await self._get_user_id_by_lemonsqueezy_id(data.attributes.customer_id, only_id=False)
        if not user_id:
            user_id = user.id
        if not user.subscription_id == data.id or not user.variant_id == data.attributes.variant_id:
            raise DBInconsistencyError(message="User cancel subscription_id does not match with the event data", uid=user_id)
        user = await self._users_repository.update_user(
            user_id=user_id,
            premium_until=data.attributes.ends_at
        )
        logger.info("User cancelled subscription", user=user)

    async def _process_subscription_event(self, event_type: WebhookEventType, data: Subscription, user_id: str | None):
        logger.debug("Processing subscription event", event_type=event_type, data=data)
        if not data.attributes.product_id == settings.lemonsqueezy_product_id:
            logger.warning("Subscription is not for our product", product_id=data.attributes.product_id, config_id=settings.lemonsqueezy_product_id)
            sentry_sdk.set_context("ls_webhook", {'data': data})
            sentry_sdk.capture_message("Subscription is not for our product")
            return
        if event_type == WebhookEventType.SUBSCRIPTION_CREATED:
            await self._handle_subscription_created(data, user_id)
        elif event_type == WebhookEventType.SUBSCRIPTION_UPDATED:
            await self._handle_subscription_updated(data, user_id)
        elif event_type == WebhookEventType.SUBSCRIPTION_CANCELLED:
            await self._handle_subscription_cancelled(data, user_id)

    async def _process_subscription_invoice_event(self, event_type: WebhookEventType, data: SubscriptionInvoice, user_id: str | None):
        logger.debug("Processing subscription invoice event", event_type=event_type, data=data)

        if event_type == WebhookEventType.SUBSCRIPTION_PAYMENT_SUCCESS:
            await self._handle_subscription_payment_success(data, user_id)
        else:
            logger.warning("Unknown event type for subscription invoice", event_type=event_type, data=data)
            sentry_sdk.set_context("ls_webhook", {'event_type': event_type, 'data': data})
            sentry_sdk.capture_message("Unknown event type for subscription invoice")
            await self._rebuild_db_state(user_id)

    async def _rebuild_db_state(self, user_id: str):
        logger.debug("Rebuilding DB state", user_id=user_id)
        try:
            self._ls_api_service = LemonsqueezyAPIService()
            customer_id = (await self._users_repository.get_user(user_id)).lemonsqueezy_id
            if not customer_id:
                logger.error("Customer ID not found for user", user_id=user_id)
                sentry_sdk.set_context("ls_webhook", {'user_id': user_id})
                sentry_sdk.capture_message("Customer ID not found for user")
                return
            is_lifetime, data = await self._ls_api_service.rebuild_premium_state(customer_id)
            if is_lifetime:
                user = await self._users_repository.update_user(
                    user_id=user_id,
                    is_premium=True,
                    premium_until=datetime.datetime.max,
                    lemonsqueezy_id=customer_id,
                    subscription_id=None,
                    tier=Tier.LIFETIME
                )
            elif data is not None:
                user = await self._users_repository.update_user(
                    user_id=user_id,
                    is_premium=True,
                    premium_until=data.attributes.renews_at,
                    lemonsqueezy_id=customer_id,
                    subscription_id=data.id,
                    variant_id=data.attributes.variant_id,
                    tier=Tier.PREMIUM
                )
            else:
                user = await self._users_repository.update_user(
                    user_id=user_id,
                    is_premium=False,
                    premium_until=None,
                    lemonsqueezy_id=customer_id,
                    subscription_id=None,
                    variant_id=None,
                    tier=Tier.FREE
                )

            logger.info("DB state rebuilt", user=user)
        except Exception as e:
            logger.error("Failed to rebuild DB state", error=repr(e))
            sentry_sdk.capture_exception(e)
            raise e

    async def _process_webhook_event(self, data: Dict[str, Any], signature: str):
        try:
            logger.debug("Processing webhook event", data=data, signature=signature)
            data = self._validate_data(data)
            user_id = data.meta.custom_data.get('user_id') if data.meta.custom_data else None

            if isinstance(data.data, Order):
                await self._process_order_event(data.meta.event_name, data.data, user_id)
            elif isinstance(data.data, Subscription):
                await self._process_subscription_event(data.meta.event_name, data.data, user_id)
            elif isinstance(data.data, SubscriptionInvoice):
                await self._process_subscription_invoice_event(data.meta.event_name, data.data, user_id)
            else:
                logger.warning("Unknown event type", data=data)
                sentry_sdk.set_context("ls_webhook", {'data': data})
                sentry_sdk.capture_message("Unknown event type")
                return

            uid = user_id if user_id else await self._get_user_id_by_lemonsqueezy_id(data.data.attributes.customer_id)
            await self._free_tier_usage_service.revalidate_user(uid)
        except DBInconsistencyError as e:
            logger.error("DB inconsistency error", error=str(e))
            sentry_sdk.capture_exception(e, extra={'data': data})
            await self._rebuild_db_state(e.uid)

    async def process_webhook_event(self, data: Dict[str, Any], signature: str):
        logger.info("Received webhook event", data=data, signature=signature)
        # we first store the raw unprocessed event
        resp = await self.table.insert({
            'payload': json.dumps(data),
            'signature': signature,
        }, count=CountMethod.exact).execute()
        if not resp.count or not resp.data:
            logger.error("Failed to save webhook event", data=data)
            sentry_sdk.set_context("ls_webhook", {'data': data})
            sentry_sdk.capture_message("Failed to save webhook event")
            raise RawWebhookStorageError("Failed to insert webhook event")
        # then we create background task to process the event asynchronously and webhook could respond immediately
        task = asyncio.create_task(self._process_webhook_event(data, signature))
        logger.info(
            "Created task to process webhook event",
            task=str(task),
            signature=signature,
            db_id=resp.data[0].get('id')
        )


if __name__ == '__main__':
    async def amain():
        service = LemonsqueezyWebhookService(
            db=await SupabaseConnectionService().connect()
        )
        await service._rebuild_db_state("0822cebf-4a35-4161-9f1f-c45fafb36c15")
    asyncio.run(amain())