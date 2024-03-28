from typing import Annotated

from fastapi import APIRouter, Depends

from app.models.usage import CurrentUsage
from app.services.usage_service import BaseUsageService, LemonSqueezyUsageService

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("/current")
async def current_usage(usage_service: Annotated[BaseUsageService, Depends(LemonSqueezyUsageService)]) -> CurrentUsage:
    return await usage_service.get_user_usage()
