from abc import ABC, abstractmethod

from app.utils.singleton import AbstractSingleton


class BaseCacheService(ABC, metaclass=AbstractSingleton):
    @abstractmethod
    async def get(self, key: str):
        raise NotImplementedError()

    @abstractmethod
    async def set(self, key: str, value: any, *args, **kwargs):
        raise NotImplementedError()

    @abstractmethod
    async def delete(self, key: str):
        raise NotImplementedError()

    @abstractmethod
    async def update(self, key: str, value: any):
        raise NotImplementedError()

    @abstractmethod
    async def incr(self, key: str, amount: int = 1):
        raise NotImplementedError()

    @abstractmethod
    async def exists(self, key: str):
        raise NotImplementedError()