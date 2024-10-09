from datetime import datetime
from typing import Tuple

import structlog
from postgrest import APIError
from postgrest.types import CountMethod
from supabase import AsyncClient

from app.models.users import User, UserWithUsage, Usage
from app.services.db.supabase import SupabaseConnectionService
from app.settings import settings

logger = structlog.getLogger(__name__)


class UserDoesNotExistError(Exception):
    pass


class FailedToCreateUserError(Exception):
    pass


class UsersRepository:
    # TODO: would be nice to absctract this into base repo, but it's not a priority
    table_name = "users"

    def __init__(self, db_client: AsyncClient):
        self.db = db_client
        self.repository = self.db.table(self.table_name)

    async def get_user(self, user_id: str) -> User:
        try:
            response = await self.repository.select("*").eq("id", user_id).single().execute()
            return User(**response.data, tier="premium" if response.data.get('is_premium') else "free")
        except APIError as e:
            if e.code == 'PGRST116':
                logger.warning("User does not exist", user_id=user_id)
                raise UserDoesNotExistError()
            logger.error("Failed to get user", error=str(e))

    async def create_user(self, user_id: str, *args, **kwargs) -> User:
        try:
            response = await self.repository.insert(
                {
                    "id": user_id,
                    **kwargs
                }, count=CountMethod.exact
            ).execute()
            if not response.count == 1:
                raise FailedToCreateUserError
            data = response.data[0]
            return User(**data, tier="premium" if data.get('is_premium') else "free")
        except APIError as e:
            logger.error("Failed to create user", error=str(e))
            raise e

    async def get_or_create_user(self, user_id: str, **kwargs) -> Tuple[User, bool]:
        try:
            user = await self.get_user(user_id)
            return user, False
        except UserDoesNotExistError:
            user = await self.create_user(user_id, **kwargs)
            return user, True

    async def update_user(self, user_id: str, **kwargs) -> User:
        data = {k: v.isoformat() if isinstance(v, datetime) else v for k, v in kwargs.items()}
        try:
            response = await self.repository.update(
                data, count=CountMethod.exact
            ).eq(
                "id", user_id
            ).execute()
            if not response.count == 1:
                raise FailedToCreateUserError
            data = response.data[0]
            return User(**data, tier="premium" if data.get('is_premium') else "free")
        except APIError as e:
            logger.error("Failed to update user", error=str(e))
            raise e

    async def _get_usage_from_db(self, user_id: str) -> Usage | None:
        response = await self.db.table("period_usage").select("*").gt(
            "time_to", datetime.now().isoformat()
        ).limit(1).execute()
        if not response.data:
            return None
        return Usage(**response.data[0])

    async def get_user_with_usage(self, user_id: str):
        try:
            user, usage = await asyncio.gather(self.get_user(user_id), self._get_usage_from_db(user_id))
            return UserWithUsage(
                **user.dict(),
                period_usage=usage.usage if usage else None,
                throttling_meta=settings.throttling_config
            )
        except APIError as e:
            if e.code == 'PGRST116':
                logger.warning("User does not exist", user_id=user_id)
                raise UserDoesNotExistError
            logger.error("Failed to get user", error=str(e))
        except BaseException as e:
            logger.error("Failed to get user", error=str(e))
            raise e

    async def get_user_by_lemonsqueezy_id(self, lemonsqueezy_id: int) -> User | None:
        try:
            resp = await self.db.table("users").select("*").eq(
                "lemonsqueezy_id",
                lemonsqueezy_id
            ).single().execute()

            return User(**resp.data)
        except APIError as e:
            if e.code == "PGRST116":
                return None


if __name__ == '__main__':
    async def amain():

        db = await SupabaseConnectionService().connect()
        repo = UsersRepository(db)
        user = await repo.get_user_with_usage("3d70da9c-51f5-46dc-bb23-31a59105d5f6")
        print(user)

    import asyncio
    asyncio.run(amain())