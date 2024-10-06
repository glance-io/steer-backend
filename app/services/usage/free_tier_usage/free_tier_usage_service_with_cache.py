import asyncio
import datetime
from typing import Tuple

import sentry_sdk
import structlog
from postgrest import APIError
from sentry_sdk import capture_exception
from supabase import AsyncClient

from app.repository.users_repository import UsersRepository
from app.services.cache.base import BaseCacheService
from app.services.usage.free_tier_usage.base import BaseFreeTierUsageService
from app.settings import settings

logger = structlog.getLogger(__name__)


class FreeTierUsageServiceWithCache(BaseFreeTierUsageService):
    _cache_usage_key = 'users:usage'
    _cache_premium_key = 'users:premium'
    _max_usage = settings.throttling_config.limit

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
                "is_premium"
                "premium_until"
            ).eq(
                "user_id", user_id
            ).single().execute()
            is_active = resp.dat.get("is_premium", False)
            valid_until = resp.dat.get("valid_until") if is_active else None
            valid_until = datetime.datetime.fromisoformat(valid_until) if valid_until else None
            return is_active, valid_until
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
                ttl = int((valid_until - datetime.datetime.now()).total_seconds())
                await self.cache.set(self._premium_key(user_id), bytes(is_premium), ttl=ttl)
            else:
                is_premium = False
                await self.cache.set(self._premium_key(user_id), bytes(is_premium), ttl=60*60)   # Effectively is premium is False, cache for 1 hour. Webhook will update it
        return bool(is_premium)

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

            time_to = datetime.datetime.fromisoformat(data["time_to"])

            if time_to < datetime.datetime.now() >= data["time_from"]:
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
                ttl = int((time_to - datetime.datetime.now()).total_seconds())
                await self.cache.set(self._usage_key(user_id), usage, ttl=ttl)
        return int(usage)

    async def _update_user_usage_db(self, user_id: str, usage_delta: int) -> Tuple[int, datetime.datetime]:
        resp = await self.db.rpc("update_or_insert_period_usage", {
            "p_uid": user_id,
            "p_date": datetime.datetime.now().isoformat(),
            "p_delta": usage_delta,
        }).execute()
        if not resp.data:
            raise ValueError("Failed to update user usage")
        usage = resp.data[0]
        return usage.get("usage", 0), datetime.datetime.fromisoformat(usage.get("time_to"))

    async def update_user_usage(self, user_id: str, usage_delta: int):
        logger.info("Updating user usage", user_id=user_id, usage_delta=usage_delta)
        usage_cache = await self.get_user_usage(user_id)
        exists = usage_cache is not None
        if exists:
            await self.cache.incr(self._usage_key(user_id), usage_delta)

        usage, time_to = await self._update_user_usage_db(user_id, usage_delta)
        logger.debug("Updated user usage in db", user_id=user_id, usage=usage, time_to=time_to)
        ttl = int((time_to - datetime.datetime.now()).total_seconds())
        if usage != usage_cache + usage_delta:
            logger.warning("Usage mismatch", user_id=user_id, usage=usage, usage_cache=usage_cache, usage_delta=usage_delta)
            sentry_sdk.capture_message(f"Usage mismatch for user {user_id}", level="warning")
        await self.cache.set(self._usage_key(user_id), usage, ttl=ttl)