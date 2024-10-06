import asyncio
import hashlib
import hmac
import json
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

    async def _process_order_event(self, event_type: WebhookEventType, data: Order):
        logger.debug("Processing order event", event_type=event_type, data=data)

    async def _process_subscription_event(self, event_type: WebhookEventType, data: Subscription, user_id: str):
        logger.debug("Processing subscription event", event_type=event_type, data=data)
        if event_type == WebhookEventType.SUBSCRIPTION_CREATED:
            user = await self._users_repository.update_user(
                user_id=user_id,
                is_premium=True,
                premium_until=data.attributes.renews_at
                # TODO: tier
            )
            logger.info("User created subscription", user=user)
        elif event_type == WebhookEventType.SUBSCRIPTION_PAYMENT_SUCCESS:
            payment_record = await self._payments_repository.create(
                user_id=user_id,
                time_from=data.attributes.paid_at,
                time_to=data.attributes.renews_at,
            )
            logger.info("Payment record created", payment_record=payment_record, user_id=user_id)
        elif event_type == WebhookEventType.SUBSCRIPTION_UPDATED:
            if data.attributes.status in self.subscription_active_states:
                user = await self._users_repository.update_user(
                    user_id=user_id,
                    is_premium=True,
                    premium_until=data.attributes.renews_at
                )
                logger.info("User updated subscription", user=user)
            else:
                user = await self._users_repository.update_user(
                    user_id=user_id,
                    is_premium=False,
                    premium_until=None
                )
                logger.info("User updated subscription", user=user)
        elif event_type == WebhookEventType.SUBSCRIPTION_CANCELLED:
            if not data.attributes.ends_at:
                logger.error("Subscription cancelled without ends_at", data=data)
                sentry_sdk.capture_message("Subscription cancelled without ends_at", extra={'data': data})
                return
            user = await self._users_repository.update_user(
                user_id=user_id,
                premium_until=data.attributes.ends_at
            )
            logger.info("User cancelled subscription", user=user, ends_at=data.attributes.ends_at)

    async def _process_webhook_event(self, data: Dict[str, Any], signature: str):
        logger.debug("Processing webhook event", data=data, signature=signature)
        data = self._validate_data(data)
        user_id = data.meta.custom_data.get('user_id')
        if not user_id:
            logger.error("User ID not found in custom data", data=data)
            sentry_sdk.capture_message("User ID not found in custom data", extra={'data': data})

        if isinstance(data.data.attributes, Order):
            await self._process_order_event(data.meta.event_name, data.data)
        elif isinstance(data.data.attributes, Subscription):
            await self._process_subscription_event(data.meta.event_name, data.data, user_id)
        else:
            logger.warning("Unknown event type", data=data)
            sentry_sdk.capture_message("Unknown event type", extra={'data': data})

    async def process_webhook_event(self, data: Dict[str, Any], signature: str):
        logger.info("Received webhook event", data=data, signature=signature)
        # we first store the raw unprocessed event
        resp = await self.table.insert({
            'payload': json.dumps(data)
        }, count=CountMethod.exact).execute()
        if not resp.count or not resp.data:
            logger.error("Failed to save webhook event", data=data)
            sentry_sdk.capture_message("Failed to save webhook event", extra={'data': data})
            raise RawWebhookStorageError("Failed to insert webhook event")
        # then we create background task to process the event asynchronously and webhook could respond immediately
        task = await asyncio.create_task(self._process_webhook_event(data, signature))
        logger.info(
            "Created task to process webhook event",
            task=str(task),
            signature=signature,
            db_id=resp.data[0].get('id')
        )