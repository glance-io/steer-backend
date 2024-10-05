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

    async def create(self, user_id: str, **kwargs):
        try:
            response = await self.repository.insert(
                {
                    "user_id": user_id,
                    **kwargs
                }, count=CountMethod.exact
            ).execute()
            return response
        except Exception as e:
            logger.error("Failed to create payment", error=str(e))
            capture_exception(e)
            raise e
