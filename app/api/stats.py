from fastapi import APIRouter

from app.models.stats import StatsResDTO
from app.services.stats_service import StatsService

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/actions")
async def get_actions() -> StatsResDTO:
    """
    Endpoint for landing page to show usage statistics
    :return: StatsResDTO
    """
    service = StatsService()
    usage = await service.get_total_usage()
    return StatsResDTO(
        usage=f"{usage:,}" ,
    )
