import asyncio
import json
import uuid
from typing import Any, Dict

import sentry_sdk
import structlog
from postgrest.types import CountMethod
from supabase import AsyncClient

from app.models.lemonsqueezy.order import Order
from app.models.lemonsqueezy.subscription import Subscription
from app.models.lemonsqueezy.webhooks import WebhookPayload, EventType as WebhookEventType
from app.repository.payments_repository import PaymentsRepository
from app.repository.users_repository import UsersRepository

logger = structlog.getLogger(__name__)


class RawWebhookStorageError(Exception):
    pass


class LemonsqueezyWebhookService:
    model = WebhookPayload
    subscription_active_states = {'on_trial', 'active', 'paused', 'past_due'}

    def __init__(self, db: AsyncClient):
        self.db = db
        self.table = self.db.table("webhook_raw")
        self._users_repository = UsersRepository(db)
        self._payments_repository = PaymentsRepository(db)

    def _validate_data(self, data: Dict[str, Any]):
        try:
            return self.model.model_validate(data)
        except Exception as e:
            logger.error("Failed to validate webhook data", data=data, error=str(e))
            sentry_sdk.capture_exception(e)
            raise e

    async def _process_order_event(self, event_type: WebhookEventType, data: Order, user_id: str | None):
        logger.debug("Processing order event", event_type=event_type, data=data)

    async def _handle_subscription_created(self, data: Subscription, user_id: str | None):
        if not user_id:
            logger.error("User ID not found in custom data", data=data)
            sentry_sdk.capture_message("User ID not found in custom data", extra={'data': data})
            raise ValueError("User ID not found in custom data")
        user = await self._users_repository.update_user(
            user_id=user_id,
            is_premium=True,
            premium_until=data.attributes.renews_at.isoformat(),
            lemonsqueezy_id=data.attributes.customer_id,
            subscription_id=data.id,
            # TODO: tier
        )
        logger.info("User created subscription", user=user)

    async def _get_user_id_by_lemonsqueezy_id(self, lemonsqueezy_id: int) -> uuid.UUID:
        user = await self._users_repository.get_user_by_lemonsqueezy_id(lemonsqueezy_id)
        if not user:
            logger.error("User not found by lemonsqueezy_id", lemonsqueezy_id=lemonsqueezy_id)
            sentry_sdk.capture_message("User not found by lemonsqueezy_id", extra={'lemonsqueezy_id': lemonsqueezy_id})
            raise ValueError("User not found by lemonsqueezy_id")
        return user.id

    async def _handle_subscription_payment_success(self, data: Subscription, user_id: str | None):
        if not user_id:
            user_id = await self._get_user_id_by_lemonsqueezy_id(data.attributes.customer_id)
        payment_record = await self._payments_repository.create(
            user_id=user_id,
            time_from=data.attributes.paid_at.isoformat(),
            time_to=data.attributes.renews_at.isoformat(),
        )
        logger.info("Payment record created", payment_record=payment_record, user_id=user_id)

    async def _handle_subscription_updated(self, data: Subscription, user_id: str | None):
        if not user_id:
            user_id = str(await self._get_user_id_by_lemonsqueezy_id(data.attributes.customer_id))
        if data.attributes.status in self.subscription_active_states:
            user = await self._users_repository.update_user(
                user_id=user_id,
                is_premium=True,
                premium_until=data.attributes.renews_at
            )
        else:
            user = await self._users_repository.update_user(
                user_id=user_id,
                is_premium=False,
                premium_until=None
            )
        logger.info("User updated subscription", user=user)

    async def _handle_subscription_cancelled(self, data: Subscription, user_id: str | None):
        if not user_id:
            user_id = str(await self._get_user_id_by_lemonsqueezy_id(data.attributes.customer_id))
        user = await self._users_repository.update_user(
            user_id=user_id,
            is_premium=False,
            premium_until=None
        )
        logger.info("User cancelled subscription", user=user)

    async def _process_subscription_event(self, event_type: WebhookEventType, data: Subscription, user_id: str | None):
        logger.debug("Processing subscription event", event_type=event_type, data=data)
        if event_type == WebhookEventType.SUBSCRIPTION_CREATED:
            await self._handle_subscription_created(data, user_id)
        elif event_type == WebhookEventType.SUBSCRIPTION_PAYMENT_SUCCESS:
            await self._handle_subscription_payment_success(data, user_id)
        elif event_type == WebhookEventType.SUBSCRIPTION_UPDATED:
            await self._handle_subscription_updated(data, user_id)
        elif event_type == WebhookEventType.SUBSCRIPTION_CANCELLED:
            await self._handle_subscription_cancelled(data, user_id)

    async def _process_webhook_event(self, data: Dict[str, Any], signature: str):
        logger.debug("Processing webhook event", data=data, signature=signature)
        data = self._validate_data(data)
        user_id = data.meta.custom_data.get('user_id') if data.meta.custom_data else None

        if isinstance(data.data, Order):
            await self._process_order_event(data.meta.event_name, data.data, user_id)
        elif isinstance(data.data, Subscription):
            await self._process_subscription_event(data.meta.event_name, data.data, user_id)
        else:
            logger.warning("Unknown event type", data=data)
            sentry_sdk.capture_message("Unknown event type", extra={'data': data})

    async def process_webhook_event(self, data: Dict[str, Any], signature: str):
        logger.info("Received webhook event", data=data, signature=signature)
        # we first store the raw unprocessed event
        resp = await self.table.insert({
            'payload': json.dumps(data),
            'signature': signature,
        }, count=CountMethod.exact).execute()
        if not resp.count or not resp.data:
            logger.error("Failed to save webhook event", data=data)
            sentry_sdk.capture_message("Failed to save webhook event", extra={'data': data})
            raise RawWebhookStorageError("Failed to insert webhook event")
        # then we create background task to process the event asynchronously and webhook could respond immediately
        task = asyncio.create_task(self._process_webhook_event(data, signature))
        logger.info(
            "Created task to process webhook event",
            task=str(task),
            signature=signature,
            db_id=resp.data[0].get('id')
        )