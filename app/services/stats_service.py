import datetime
import json

import httpx
import sentry_sdk
import structlog

from app.services.cache.redis_cache import RedisCacheService
from app.settings import settings

logger = structlog.getLogger(__name__)


class StatsService:
    cache_key = 'stats:usage'

    def __init__(self):
        self.cache = RedisCacheService()

    async def _get_usage_cache(self):
        return await self.cache.get(self.cache_key)

    async def _get_usage_mixpanel(self) -> int:
        async with httpx.AsyncClient(
            headers={
                "Authorization": f'Basic {settings.mixpanel_api_key}',
                "Accept": "text/plain"
            }
        ) as client:
            params = {
                "from_date": datetime.date(2024, 3, 1).isoformat(),
                "to_date": datetime.date.today().isoformat(),
                "event": json.dumps(["selected-action"]),
                "project_id": 3280653,
            }
            resp = await client.get("https://data.mixpanel.com/api/2.0/export", params=params)
            resp.raise_for_status()
            data = resp.text
            return int(len(data.splitlines()) / 1.5)   # JSONL is returned, returns not only rewrites, so magic constant division

    async def get_total_usage(self):
        try:
            usage = int(await self._get_usage_cache())
            if usage:
                return usage
        except BaseException as e:
            logger.warning("Failed to get usage from cache", error=str(e))

        try:
            usage = await self._get_usage_mixpanel()
            await self.cache.set(self.cache_key, usage, ttl=60 * 60 * 72)   # Cache for 72 hours
            return usage
        except BaseException as e:
            logger.error("Failed to get usage from Mixpanel", error=str(e))
            raise e