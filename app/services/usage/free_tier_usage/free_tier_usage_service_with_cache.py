import asyncio
import datetime
from typing import Tuple

import structlog
from postgrest import APIError
from sentry_sdk import capture_exception
from supabase import AsyncClient

from app.services.cache.base import BaseCacheService
from app.services.usage.free_tier_usage.base import BaseFreeTierUsageService


logger = structlog.getLogger(__name__)


class FreeTierUsageServiceWithCache(BaseFreeTierUsageService):
    _cache_usage_key = 'users:usage'
    _cache_premium_key = 'users:premium'
    _max_usage = 10

    def __init__(self, cache: BaseCacheService, db: AsyncClient):
        self.cache = cache
        self.db = db

    def _usage_key(self, user_id: str):
        return f'{self._cache_usage_key}:{user_id}'

    def _premium_key(self, user_id: str):
        return f'{self._cache_premium_key}:{user_id}'

    async def _is_user_premium_db(self, user_id: str) -> Tuple[bool, datetime.datetime | None]:
        try:
            resp = await self.db.table("users").select(
                "id",
                "is_subscription_active:subscription(is_active)",
                "valid_until:subscription_payments(valid_until.max())"
            ).eq("id", user_id).single().execute()
            return resp.data["is_subscription_active"]
        except APIError as e:
            if e.code == "PGRST116":
                logger.warning("User not found", user_id=user_id)
                return False, None
            raise e
        except BaseException as e:
            logger.warning("Failed processing user premium status", user_id=user_id, error=str(e))
            return False, None

    async def is_user_premium(self, user_id: str) -> bool:
        is_premium = await self.cache.get(self._premium_key(user_id))
        if is_premium is None:
            is_premium, valid_until = await self._is_user_premium_db(user_id)
            if is_premium and valid_until and valid_until > datetime.datetime.now():
                ttl = (valid_until - datetime.datetime.now()).total_seconds()
                await self.cache.set(self._premium_key(user_id), is_premium, ttl=ttl)
            else:
                is_premium = False
            await self.cache.set(self._premium_key(user_id), is_premium)
        return is_premium

    async def is_user_allowed(self, user_id: str) -> bool:
        premium, usage = await asyncio.gather(
            self.is_user_premium(user_id),
            self.get_user_usage(user_id)
        )
        return premium or usage < self._max_usage

    async def _get_user_usage_db(self, user_id: str) -> Tuple[int, datetime.datetime | None]:
        try:
            resp = await self.db.table("period_usage").select(
                "time_from",
                "time_to",
                "usage"
            ).eq("user_id", user_id).order(
                "time_to", desc=True
            ).limit(1).execute()

            if not resp.data:
                return 0, None
            data = resp.data[0]

            if data["time_to"] < datetime.datetime.now() >= data["time_from"]:
                return data["usage"]
            return 0, None
        except APIError as e:
            if e.code == "PGRST116":
                logger.warning("User not found", user_id=user_id)
                return 0, None
            capture_exception(e)
            raise e
        except BaseException as e:
            logger.warning("Failed processing user usage", user_id=user_id, error=str(e))
            capture_exception(e)
            return 0, None

    async def get_user_usage(self, user_id: str) -> int:
        usage = await self.cache.get(self._usage_key(user_id))
        if usage is None:
            usage, time_to = await self._get_user_usage_db(user_id)
            if time_to and time_to > datetime.datetime.now():
                ttl = (time_to - datetime.datetime.now()).total_seconds()
                await self.cache.set(self._usage_key(user_id), usage, ttl=ttl)
            else:
                await self.cache.set(self._usage_key(user_id), usage)
        return usage

    async def update_user_usage(self, user_id: str, usage_delta: int):
        raise NotImplementedError()