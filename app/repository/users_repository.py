from datetime import datetime

import structlog
from openai import APIError
from supabase import AsyncClient

from app.models.users import User, UserWithUsage
from app.services.db.supabase import SupabaseConnectionService

logger = structlog.getLogger(__name__)


class UserDoesNotExistError(Exception):
    pass


class UsersRepository:
    table_name = "users"

    def __init__(self, db_client: AsyncClient):
        self.db = db_client
        self.repository = self.db.table(self.table_name)

    async def get_user(self, user_id: str):
        try:
            response = await self.repository.select("*").eq("id", user_id).single().execute()
            return User(**response.data)
        except APIError as e:
            if e.code == 'PGRST116':
                logger.warning("User does not exist", user_id=user_id)
                raise UserDoesNotExistError
            logger.error("Failed to get user", error=str(e))

    async def get_user_with_usage(self, user_id: str):
        try:
            response = await self.repository.select(
                "*",
                "usage:period_usage!inner(*)"
            ).eq("id", user_id).gte("period_usage.time_to", datetime.now().isoformat()).limit(1).single().execute()
            if not response.data:
                raise UserDoesNotExistError
            data = response.data
            usage = data.pop("usage")
            if isinstance(usage, list) and usage:
                data["usage"] = usage[0]
            return UserWithUsage(**data)
        except APIError as e:
            if e.code == 'PGRST116':
                logger.warning("User does not exist", user_id=user_id)
                raise UserDoesNotExistError
            logger.error("Failed to get user", error=str(e))


if __name__ == '__main__':
    async def amain():

        db = await SupabaseConnectionService().connect()
        repo = UsersRepository(db)
        user = await repo.get_user_with_usage("3d70da9c-51f5-46dc-bb23-31a59105d5f6")
        print(user)

    import asyncio
    asyncio.run(amain())