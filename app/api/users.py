import asyncio
import datetime

import sentry_sdk
from fastapi import APIRouter, HTTPException, Depends
from postgrest import APIError
from starlette.responses import RedirectResponse
from supabase import AsyncClient

from app.depends.auth import auth_dependency
from app.models.tier import Tier
from app.models.users import SignInDTO, UserWithUsage
from app.repository.users_repository import UsersRepository, UserDoesNotExistError
from app.services.db.supabase import SupabaseConnectionService
from app.services.lemon_squeezy_service import LemonSqueezyService
from gotrue.types import User as AuthUser

from app.tasks.check_subscription import check_existing_subscription

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/signin")
async def sign_in(data: SignInDTO, db: AsyncClient = Depends(SupabaseConnectionService().connect), auth_user: AuthUser = Depends(auth_dependency)):
    users_repo = UsersRepository(db)
    user, created = await users_repo.get_or_create_user(
        auth_user.id,
        email=auth_user.email,
        license_key=data.license_key,
        instance_id=data.instance_id
    )

    if created and data.license_key and data.instance_id:
        ls_service = LemonSqueezyService()
        try:
            subscription_detail, is_premium, is_lifetime = await ls_service.pair_existing_license_with_user(
                user_id=auth_user.id,
                license_key=data.license_key,
                instance_id=data.instance_id
            )
        except Exception as e:
            sentry_sdk.capture_exception(e)
            subscription_detail, is_premium, is_lifetime = None, False, False

        if is_lifetime:
            user = await users_repo.update_user(
                auth_user.id,
                is_premium=True,
                premium_until=datetime.datetime.max,
                tier=Tier.LIFETIME
            )
        elif is_premium and subscription_detail:
            user = await users_repo.update_user(
                auth_user.id,
                is_premium=is_premium,
                premium_until=subscription_detail.attributes.renews_at if subscription_detail else None,
                subscription_id=subscription_detail.id if subscription_detail else None,
                lemonsqueezy_id=subscription_detail.attributes.customer_id if subscription_detail else None,
                variant_id=subscription_detail.attributes.variant_id if subscription_detail else None,
                tier=Tier.FREE if not is_premium else Tier.PREMIUM if not is_lifetime else Tier.LIFETIME
            )

    if created:
        try:
            # noinspection PyAsyncCall
            asyncio.create_task(check_existing_subscription(auth_user.id, auth_user.email))
        except Exception as e:
            sentry_sdk.capture_exception(e)

    return {"is_premium": user.is_premium}


@router.get("/{user_id}/profile")
async def get_profile(
        user_id: str,
        db = Depends(SupabaseConnectionService().connect),
        _auth_user: AuthUser = Depends(auth_dependency)
) -> UserWithUsage:
    repo = UsersRepository(db)
    try:
        return await repo.get_user_with_usage(user_id)
    except UserDoesNotExistError:
        raise HTTPException(status_code=404, detail="User not found")
    except APIError as e:
        raise HTTPException(status_code=500, detail="DB error")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/checkout")
async def get_checkout_link(uid: str, email: str, ls_api_service=Depends(LemonSqueezyService)):
    checkout = await ls_api_service.create_checkout(uid, email)
    return RedirectResponse(url=checkout.attributes.url)
