from typing import Any, Optional

import redis.asyncio as redis
from app.services.cache.base import BaseCacheService
from app.settings import settings
from app.utils.singleton import Singleton


class RedisCacheService(BaseCacheService):
    _instance = None

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None , *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, "_initialized"):
            self.host = host or settings.redis_host
            self.port = port or settings.redis_port
            self.redis: redis.Redis | None = None

    async def connect(self):
        pool = redis.ConnectionPool(host=self.host, port=self.port)
        self.redis = redis.Redis(connection_pool=pool)

    async def disconnect(self):
        if self.redis:
            await self.redis.close()

    async def get(self, key: str) -> Any:
        if not self.redis:
            raise RuntimeError("Redis connection not established")
        try:
            return await self.redis.get(key)
        except Exception as e:
            print(f"Error getting value for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = None, keep_ttl: Optional[bool] = False) -> bool:
        if not self.redis:
            raise RuntimeError("Redis connection not established")
        try:
            await self.redis.set(key, value, ex=ttl, keepttl=keep_ttl)
            return True
        except Exception as e:
            print(f"Error setting value for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        if not self.redis:
            raise RuntimeError("Redis connection not established")
        try:
            deleted_count = await self.redis.delete(key)
            return deleted_count > 0
        except Exception as e:
            print(f"Error deleting key {key}: {e}")
            return False

    async def update(self, key: str, value: Any) -> bool:
        if not self.redis:
            raise RuntimeError("Redis connection not established")
        try:
            await self.redis.set(key, value)
            return True
        except Exception as e:
            print(f"Error updating value for key {key}: {e}")
            return False

    async def incr(self, key: str, amount: int = 1) -> int:
        if not self.redis:
            raise RuntimeError("Redis connection not established")
        try:
            return await self.redis.incr(key, amount)
        except Exception as e:
            print(f"Error incrementing key {key}: {e}")
            return -1

    async def get_ttl(self, key: str) -> int:
        if not self.redis:
            raise RuntimeError("Redis connection not established")
        try:
            return await self.redis.ttl(key)
        except Exception as e:
            print(f"Error getting TTL for key {key}: {e}")
            return -1

    async def exists(self, key: str) -> bool:
        if not self.redis:
            raise RuntimeError("Redis connection not established")
        try:
            return await self.redis.exists(key)
        except Exception as e:
            print(f"Error checking if key exists {key}: {e}")
            return False


if __name__ == '__main__':
    class_a = RedisCacheService()
    class_b = RedisCacheService()

    print(id(class_a) == id(class_b))  # True