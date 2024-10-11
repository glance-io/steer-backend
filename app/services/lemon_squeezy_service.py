import asyncio
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any

import httpx
import sentry_sdk
import structlog
from postgrest.types import CountMethod
from supabase import AsyncClient

from app.models.lemonsqueezy.checkout import CheckoutResponse, Checkout
from app.models.lemonsqueezy.customer import Customer, CustomerResponse
from app.models.lemonsqueezy.license import LicenseResponse
from app.models.lemonsqueezy.order import OrderMultiResponse, Status as OrderStatus, OrderItem
from app.models.lemonsqueezy.price import Price, PriceResponse
from app.models.lemonsqueezy.subscription import SubscriptionResponse, SubscriptionAttributes, Subscription, \
    SubscriptionMultiResponse
from app.models.lemonsqueezy.variant import Variant, VariantResponse
from app.settings import settings

logger = structlog.getLogger(__name__)


class LicenseNotActiveException(Exception):
    pass


class LemonSqueezyService:
    # TODO: Improve handling of requests so the public methods don't rely on the client being passed in
    api_url = "https://api.lemonsqueezy.com/v1"
    subscription_active_states = {'on_trial', 'active', 'paused', 'past_due', 'cancelled'}

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

    async def get_product_variant_detail(self, product_variant_id: int, client: httpx.AsyncClient) -> Tuple[Variant, Price]:
        response_variant = await client.get(
            f"{self.api_url}/variants/{product_variant_id}"
        )
        response_variant.raise_for_status()
        variant = VariantResponse.parse_obj(response_variant.json())

        response_price = await client.get(
            variant.data.relationships.price_model.links.related
        )
        response_price.raise_for_status()
        price = PriceResponse.parse_obj(response_price.json())
        return variant.data, price.data

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

    async def get_subscription_detail(self, subscription_id: int, client: httpx.AsyncClient) -> Subscription:
        response = await client.get(
            f"{self.api_url}/subscriptions/{subscription_id}"
        )
        response.raise_for_status()
        subscription_response = SubscriptionResponse(**response.json())
        return subscription_response.data

    async def get_customer(self, customer_id: int, client: httpx.AsyncClient) -> Customer:
        response = await client.get(
            f"{self.api_url}/customers/{customer_id}"
        )
        response.raise_for_status()
        return CustomerResponse(**response.json()).data

    async def rebuild_premium_state(self, customer_id: int) -> Tuple[bool, Subscription | OrderItem | None]:
        async with httpx.AsyncClient(
                headers={"Authorization": f"Bearer {settings.lemonsqueezy_api_key}"},
                timeout=30,
        ) as client:
            customer = await self.get_customer(customer_id, client)
            orders_link = customer.relationships.orders.links.related
            subscriptions_link = customer.relationships.subscriptions.links.related
            responses = await asyncio.gather(
                client.get(orders_link),
                client.get(subscriptions_link)
            )
            for resp in responses:
                resp.raise_for_status()
            orders_resp, subscriptions_resp = (
                OrderMultiResponse(**responses[0].json()),
                SubscriptionMultiResponse(**responses[1].json())
            )
            orders = [
                o for o in orders_resp.data
                if o.attributes.first_order_item.product_id == settings.lemonsqueezy_product_id
            ]
            for order in orders:
                product_detail = await self.get_product_variant_detail(order.attributes.first_order_item.variant_id, client)
                if order.attributes.status == OrderStatus.PAID and product_detail[1].attributes.is_lifetime:
                    return True, order.attributes.first_order_item
            subscriptions = [
                s for s in subscriptions_resp.data
                if s.attributes.product_id == settings.lemonsqueezy_product_id
                and s.attributes.status in self.subscription_active_states
            ]
            if subscriptions:
                return False, subscriptions[0]
            return False, None

    async def pair_existing_license_with_user(self, user_id: str, license_key: str, instance_id: str) -> Tuple[Subscription | None, bool, bool]:
        try:
            async with (httpx.AsyncClient(
                    headers={"Authorization": f"Bearer {settings.lemonsqueezy_api_key}"}
            ) as client):
                ls_license = await self.validate_license(license_key, instance_id, client)
                if not ls_license.valid or not ls_license.license_key.status == 'active':
                    logger.info(
                        "Submitted inactive license", user_id=user_id, license_key=license_key, instance_id=instance_id
                    )
                    return None, False, False
                if not ls_license.meta.product_id == settings.lemonsqueezy_product_id:
                    raise ValueError(f"Invalid product id: {ls_license.meta.product_id}")

                subscription_item_id = await self.__get_subscription_item_from_order_product(
                    ls_license.meta.order_item_id, client
                )
                variant, price = await self.get_product_variant_detail(ls_license.meta.variant_id, client)
                if price.attributes.is_subscription:
                    subscription_detail = await self.get_subscription_detail(subscription_item_id, client)
                else:
                    subscription_detail = None
                return (
                    subscription_detail,
                    subscription_detail.attributes.status in self.subscription_active_states,
                    price.attributes.is_lifetime
                )
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP status Error Lemon Squeezy: {e}")
            sentry_sdk.capture_exception(e)
            raise ValueError(f"Failed to validate license: {e}")

    async def create_checkout(self, user_id: str, email: str) -> Checkout:
        # only implements the minimum required fields
        async with httpx.AsyncClient(
                headers={"Authorization": f"Bearer {settings.lemonsqueezy_api_key}"}
        ) as client:
            try:
                response = await client.post(
                    f"{self.api_url}/checkouts",
                    json={
                        "data": {
                            "type": "checkouts",
                            "attributes": {
                                "store_id": settings.lemonsqueezy_store_id,
                                "checkout_data": {
                                    "email": email,
                                    "custom": {
                                        "user_id": user_id
                                    }
                                },
                            },
                            "relationships": {
                                "store": {
                                    "data": {
                                        "type": "stores",
                                        "id": settings.lemonsqueezy_store_id
                                    }
                                },
                                "variant": {
                                    "data": {
                                        "type": "variants",
                                        "id": settings.lemonsqueezy_default_variant_id
                                    }
                                }
                            }
                        }
                    }
                )
                response.raise_for_status()
                return CheckoutResponse(**response.json()).data
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP status Error Lemon Squeezy: {e}", content=e.response.content)
                raise e
