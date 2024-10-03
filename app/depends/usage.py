from app.services.cache.redis_cache import RedisCacheService
from app.services.db.supabase import SupabaseConnectionService
from app.services.usage.free_tier_usage.base import BaseFreeTierUsageService
from app.services.usage.free_tier_usage.free_tier_usage_service_with_cache import FreeTierUsageServiceWithCache


async def get_usage_service() -> BaseFreeTierUsageService:
    db = await SupabaseConnectionService().connect()
    service = FreeTierUsageServiceWithCache(
        cache=RedisCacheService(),
        db=db
    )
    return service
