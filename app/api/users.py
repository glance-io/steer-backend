from fastapi import APIRouter, HTTPException, Depends
from postgrest import APIError

from app.depends.auth import auth_dependency
from app.models.users import SignInDTO, UserWithUsage
from app.repository.users_repository import UsersRepository, UserDoesNotExistError
from app.services.db.supabase import SupabaseConnectionService
from app.services.lemon_squeezy_service import LemonSqueezyService
from gotrue.types import User as AuthUser

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/signin")
async def sign_in(data: SignInDTO):
    db = await SupabaseConnectionService().connect()
    try:
        user_record_respone = await db.table("users").insert({
            'id': data.user_id,
        }, count='exact').execute()
        if not user_record_respone.count == 1:
            raise HTTPException(status_code=500, detail="Failed to create user")
    except APIError as e:
        if e.code == '23505':
            pass
        else:
            raise HTTPException(status_code=500, detail="Failed to create user", error=str(e))

    ls_service = LemonSqueezyService(db=db)
    is_premium = await ls_service.pair_existing_license_with_user(
        user_id=data.user_id,
        license_key=data.license_key,
        instance_id=data.instance_id
    )
    return {"is_premium": is_premium}


@router.get("{user_id}/profile")
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
