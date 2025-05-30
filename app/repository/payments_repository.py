from datetime import datetime

import structlog
from postgrest.types import CountMethod
from sentry_sdk import capture_exception
from supabase import AsyncClient

logger = structlog.getLogger(__name__)


class PaymentsRepository:
    table_name = "subscription_payments"

    def __init__(self, db: AsyncClient):
        self.db = db
        self.repository = self.db.table(self.table_name)

    async def create(self, user_id: str | None, **kwargs):
        data = {k: v.isoformat() if isinstance(v, datetime) else v for k, v in kwargs.items()}
        try:
            response = await self.repository.insert(
                {
                    "user_id": user_id,
                    **data
                }, count=CountMethod.exact
            ).execute()
            if not response.count:
                raise Exception("No rows affected by insert")
            return response.data[0]
        except Exception as e:
            logger.error("Failed to create payment", error=str(e))
            capture_exception(e)
            raise e


    async def get_records_by_email(self, email: str):
        response = await self.repository.select("*").eq("email", email).order("created_at", desc=True).execute()
        return response.data
