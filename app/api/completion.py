from typing import Annotated, List
from fastapi import Depends, APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse
from app.depends.llm import get_llm_service
from app.services.rewrite_service import RewriteService
from app.services.text_highlighting_service import TextHighlightingService
from app.services.llm_service import LLMServiceBase
from app.models.completion import RephraseRequest
import structlog

router = APIRouter(prefix="/completion", tags=["completion"])

logger = structlog.get_logger(__name__)


@router.post("/rephrase")
async def rephrase(request: RephraseRequest, llm_service: LLMServiceBase = Depends(get_llm_service)):
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=403, detail="Missing users credentials")
    try:
        rewrite_service = RewriteService(request, llm_service)
        return EventSourceResponse(rewrite_service.rewrite(
            sse_formating=True)
        )
    except Exception as e:
        logger.error(f"Error in rephrase: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/highlight")
def highlight(highlighting_service: Annotated[TextHighlightingService, Depends(TextHighlightingService)]) -> List[int]:
    return highlighting_service.create_highlight_list()
