from typing import Annotated

import structlog
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.requests import Request
from gotrue.errors import AuthError

from app.services.db.supabase import SupabaseConnectionService

logger = structlog.get_logger(__name__)


async def auth_dependency(
        request: Request,
        auth: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer(auto_error=False))]
):
    logger.info("Checking for authorization token")

    if not auth:
        raise HTTPException(status_code=401, detail="Authorization token not found")

    auth_token = auth.credentials

    supabase = await SupabaseConnectionService().connect()
    try:
        user_response = await supabase.auth.get_user(jwt=auth_token)
        if not (user_response and user_response.user):
            raise HTTPException(status_code=401, detail="User not found")

        # You can optionally set the user in request.state if needed
        request.state.user = user_response.user

        return user_response.user
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
