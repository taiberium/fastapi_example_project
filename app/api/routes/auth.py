from fastapi import APIRouter, Depends

from app.api.dependencies import get_auth_service, get_current_active_user
from app.entities.user import User
from app.core.exceptions import get_credential_exception
from app.schemas.auth import GoogleLoginRequest, Token, UserRead
from app.service.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/google", response_model=Token)
async def login_with_google(
    data: GoogleLoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> Token:
    result = auth_service.login_with_google(data.id_token)
    if result is None:
        raise get_credential_exception(detail="Invalid Google token")
    _user, access_token = result
    return Token(access_token=access_token)


@router.get("/me", response_model=UserRead)
async def read_current_user(
    current_user: User = Depends(get_current_active_user),
) -> UserRead:
    return UserRead.model_validate(current_user)
