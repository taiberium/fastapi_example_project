from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.guards import CurrentActiveUser
from app.core.exceptions import get_credential_exception
from app.schemas.auth import GoogleLoginRequest, Token, UserRead
from app.service.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

# Route-level DI aliases — the service self-wires its repository.
AuthServiceDep = Annotated[AuthService, Depends(AuthService)]
ActiveUserDep = Annotated[CurrentActiveUser, Depends(CurrentActiveUser)]


@router.post("/google", response_model=Token)
async def login_with_google(
    data: GoogleLoginRequest,
    auth_service: AuthServiceDep,
) -> Token:
    result = auth_service.login_with_google(data.id_token)
    if result is None:
        raise get_credential_exception(detail="Invalid Google token")
    _user, access_token = result
    return Token(access_token=access_token)


@router.get("/me", response_model=UserRead)
async def read_current_user(
    current: ActiveUserDep,
) -> UserRead:
    return UserRead.model_validate(current.user)
