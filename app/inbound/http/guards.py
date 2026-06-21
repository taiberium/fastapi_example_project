"""Web-layer auth guards as class-based FastAPI dependencies.

Each guard resolves the authenticated user in its constructor and exposes it as
`.user`. They chain through `__init__`: superuser -> active -> current.
"""

from typing import Annotated

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import get_credential_exception
from app.core.security import decode_access_token
from app.entities.user import User
from app.service.auth_service import AuthService

bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    """Decode the app JWT from the Authorization header and load the user."""

    def __init__(
        self,
        auth_service: Annotated[AuthService, Depends(AuthService)],
        credentials: Annotated[
            HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
        ] = None,
    ):
        if credentials is None:
            raise get_credential_exception(detail="Not authenticated")

        payload = decode_access_token(credentials.credentials)
        if payload is None or payload.get("sub") is None:
            raise get_credential_exception()

        try:
            user_id = int(payload["sub"])
        except (TypeError, ValueError):
            raise get_credential_exception() from None

        user = auth_service.get_user_by_id(user_id)
        if user is None:
            raise get_credential_exception(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        self.user: User = user


class CurrentActiveUser:
    def __init__(self, current: Annotated[CurrentUser, Depends(CurrentUser)]):
        if not current.user.is_active:
            raise get_credential_exception(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
            )
        self.user: User = current.user


class CurrentSuperuser:
    def __init__(self, current: Annotated[CurrentActiveUser, Depends(CurrentActiveUser)]):
        if not current.user.is_superuser:
            raise get_credential_exception(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user does not have enough privileges",
            )
        self.user: User = current.user
