from abc import ABC, abstractmethod


class BaseFreeTierUsageService(ABC):
    @abstractmethod
    async def is_user_premium(self, user_id: str) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def is_user_allowed(self, user_id: str) -> bool:
        raise NotImplementedError()

    @abstractmethod
    async def get_user_usage(self, user_id: str) -> int:
        raise NotImplementedError()

    @abstractmethod
    async def update_user_usage(self, user_id: str, usage_delta: int):
        raise NotImplementedError()