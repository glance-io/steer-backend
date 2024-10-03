from abc import ABC, abstractmethod

from app.utils.singleton import AbstractSingleton


class BaseDBConnectionService(ABC, metaclass=AbstractSingleton):
    db = None

    @abstractmethod
    async def _connect(self, **kwargs):
        raise NotImplementedError()

    async def connect(self):
        if self.db is None:
            return await self._connect()
        return self.db

