from app.services.cache.redis_cache import RedisCacheService
from app.services.db.supabase import SupabaseConnectionService
from app.services.usage.free_tier_usage.base import BaseFreeTierUsageService
from app.services.usage.free_tier_usage.free_tier_usage_service_with_cache import FreeTierUsageServiceWithCache


async def get_usage_service() -> BaseFreeTierUsageService:
    service = FreeTierUsageServiceWithCache(
        cache=RedisCacheService(),
        db=await SupabaseConnectionService().connect()
    )
    return service
