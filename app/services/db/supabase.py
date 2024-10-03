from supabase import AsyncClient
from supabase.lib.client_options import ClientOptions, AsyncClientOptions

from app.services.db.base import BaseDBConnectionService
from supabase.client import create_async_client

from app.settings import settings


class SupabaseConnectionService(BaseDBConnectionService):
    _db: AsyncClient | None =  None

    async def _connect(self, **kwargs):
        if not self.db:
            self.db = await create_async_client(
                settings.db_config.url,
                settings.db_config.password,
                AsyncClientOptions(
                    **kwargs
                )
            )
        return self.db
