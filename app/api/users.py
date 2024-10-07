from fastapi import APIRouter, HTTPException, Depends
from postgrest import APIError
from supabase import AsyncClient

from app.depends.auth import auth_dependency
from app.models.users import SignInDTO, UserWithUsage
from app.repository.payments_repository import PaymentsRepository
from app.repository.users_repository import UsersRepository, UserDoesNotExistError
from app.services.db.supabase import SupabaseConnectionService
from app.services.lemon_squeezy_service import LemonSqueezyService
from gotrue.types import User as AuthUser

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

    if created:
        ls_service = LemonSqueezyService(db=db)
        payments_repo = PaymentsRepository(db=db)
        subscription_detail, is_premium = await ls_service.pair_existing_license_with_user(
            user_id=auth_user.id,
            license_key=data.license_key,
            instance_id=data.instance_id
        )
        user = await users_repo.update_user(
            auth_user.id,
            is_premium=is_premium,
            subscription_id=subscription_detail.subscription_id,
            lemonsqueezy_id=subscription_detail.customer_id
        )
        await payments_repo.create(
            user_id=auth_user.id,
            valid_from=subscription_detail.valid_from.isoformat(),
            valid_until=subscription_detail.valid_until.isoformat(),
        )

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
