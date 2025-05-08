import uuid
from typing import Annotated, List

import sentry_sdk
from fastapi import Depends, APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse
from app.depends.llm import get_llm_service
from app.depends.usage import get_usage_service
from app.services.rewrite.rewrite_manager import RewriteManager
from app.services.text_highlighting_service import TextHighlightingService
from app.services.llm.llm_service import LLMServiceBase
from app.models.completion import RephraseRequest
import structlog

from app.services.usage.free_tier_usage.base import BaseFreeTierUsageService

router = APIRouter(prefix="/completion", tags=["completion"])

logger = structlog.get_logger(__name__)


@router.post("/v2/rephrase")
async def rephrase_new(
        request: RephraseRequest,
        llm_service: LLMServiceBase = Depends(get_llm_service),
        usage_service: BaseFreeTierUsageService = Depends(get_usage_service)
):
    is_valid_user_id = True
    try:
        _ = uuid.UUID(request.uid)
    except ValueError as e:
        sentry_sdk.capture_message(f'Invalid user id - {request.uid}, {repr(e)}')
        is_valid_user_id = False
    try:
        rewrite_service = RewriteManager(usage_service=usage_service if is_valid_user_id else None)
        return EventSourceResponse(rewrite_service.rewrite(request))
    except Exception as e:
        logger.error(f"Error in rephrase: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/highlight")
def highlight(highlighting_service: Annotated[TextHighlightingService, Depends(TextHighlightingService)]) -> List[int]:
    return highlighting_service.create_highlight_list()
