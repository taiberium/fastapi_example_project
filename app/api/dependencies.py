from typing import Tuple

from fastapi import Depends, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.entities.user import User
from app.core.exceptions import get_credential_exception
from app.persistence.db.db import get_db
from app.core.security import decode_access_token
from app.service.auth_service import AuthService
from app.service.person_service import PersonService

bearer_scheme = HTTPBearer(auto_error=False)


def get_pagination_params(
    skip: int = Query(0, ge=0), limit: int = Query(10, gt=0)
) -> Tuple[int, int]:
    """Return (skip, limit) pagination parameters from the query string."""
    return skip, limit


def get_person_service(db: Session = Depends(get_db)) -> PersonService:
    return PersonService(db)


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """Decode the app JWT from the Authorization header and load the user."""
    if credentials is None:
        raise get_credential_exception(detail="Not authenticated")

    payload = decode_access_token(credentials.credentials)
    if payload is None or payload.get("sub") is None:
        raise get_credential_exception()

    user = auth_service.get_user_by_id(int(payload["sub"]))
    if user is None:
        raise get_credential_exception(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise get_credential_exception(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user


def get_current_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if not current_user.is_superuser:
        raise get_credential_exception(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have enough privileges",
        )
    return current_user
