from typing import Annotated

from fastapi import Depends, APIRouter
from app.services.rewrite_service import RewriteService
from sse_starlette.sse import EventSourceResponse

from app.services.text_highlighting_service import TextHighlightingService

router = APIRouter(prefix="/completion", tags=["completion"])


@router.post("/rephrase")
def rephrase(rephrase_service: Annotated[RewriteService, Depends(RewriteService)]):
    async def sse_serializer():
        async for data in rephrase_service.rewrite():
            yield {
                "data": data,
                "event": "data"
            }
    return EventSourceResponse(sse_serializer())


@router.get("/highlight")
def highlight(highlighting_service: Annotated[TextHighlightingService, Depends(TextHighlightingService)]):
    return highlighting_service.create_highlight_list()
