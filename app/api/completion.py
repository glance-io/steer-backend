from typing import Annotated

from fastapi import Depends, APIRouter
from app.services.rewrite_service import RewriteService
from sse_starlette.sse import EventSourceResponse


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
