from typing import Annotated, List

from fastapi import Depends, APIRouter
from app.services.rewrite_service import RewriteService
from sse_starlette.sse import EventSourceResponse

from app.services.text_highlighting_service import TextHighlightingService

router = APIRouter(prefix="/completion", tags=["completion"])


@router.post("/rephrase")
def rephrase(rephrase_service: Annotated[RewriteService, Depends(RewriteService)]):
    return EventSourceResponse(rephrase_service.rewrite(sse_formating=True))


@router.get("/highlight")
def highlight(highlighting_service: Annotated[TextHighlightingService, Depends(TextHighlightingService)]) -> List[int]:
    return highlighting_service.create_highlight_list()
