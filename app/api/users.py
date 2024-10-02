from fastapi import APIRouter

from app.models.users import SignInDTO

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/signin")
async def sign_in(data: SignInDTO):
    return {"message": "User signed in"}