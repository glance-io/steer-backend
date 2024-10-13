import hmac
from typing import Dict, Any

import structlog
from fastapi import APIRouter, HTTPException, Depends
from sentry_sdk import capture_message, capture_exception, set_extra, set_context
from starlette.requests import Request

from app.services.db.supabase import SupabaseConnectionService
from app.services.webhooks.lemonsqueezy import LemonsqueezyWebhookService
from app.settings import settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

loggger = structlog.getLogger(__name__)


@router.post("/lemonsqueezy")
async def lemonsqueezy_webhook(
        data: Dict[str, Any],
        req: Request,
        db=Depends(SupabaseConnectionService().connect)
):
    try:
        # validate secret
        signature = req.headers.get("X-Signature")
        if not signature:
            raise HTTPException(status_code=403, detail="Missing signature header")
        validation_signature = hmac.new(settings.lemonsqueezy_webhook_secret.encode(), await req.body(), "sha256").hexdigest()
        if not hmac.compare_digest(signature, validation_signature):
            loggger.error("Invalid signature", signature=signature, validation_signature=validation_signature)
            set_context({"signature": signature, "validation_signature": validation_signature, "data": data})
            capture_message("Invalid signature")
            raise HTTPException(status_code=403, detail="Invalid signature")

        webhook_service = LemonsqueezyWebhookService(
            db=db
        )
        await webhook_service.process_webhook_event(data, signature)
        return {"status": "ok"}
    except Exception as e:
        loggger.error("Failed to process webhook", error=str(e))
        capture_exception(e)
        raise HTTPException(status_code=500, detail="Failed to process webhook")