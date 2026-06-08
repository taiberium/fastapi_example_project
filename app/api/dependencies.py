from fastapi import Depends, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import get_credential_exception
from app.core.security import decode_access_token
from app.entities.user import User
from app.persistence.db.db import get_db
from app.persistence.repository.membership_repository import MembershipRepository
from app.persistence.repository.person_repository import PersonRepository
from app.persistence.repository.user_repository import UserRepository
from app.service.auth_service import AuthService
from app.service.person_service import PersonService

bearer_scheme = HTTPBearer(auto_error=False)


def get_pagination_params(
    skip: int = Query(0, ge=0), limit: int = Query(10, gt=0)
) -> tuple[int, int]:
    """Return (skip, limit) pagination parameters from the query string."""
    return skip, limit


# DI chain: get_db -> repository (holds the session) -> service (holds the repository).
def get_person_repository(db: Session = Depends(get_db)) -> PersonRepository:
    return PersonRepository(db)


def get_membership_repository(db: Session = Depends(get_db)) -> MembershipRepository:
    return MembershipRepository(db)


def get_person_service(
    repository: PersonRepository = Depends(get_person_repository),
    membership_repository: MembershipRepository = Depends(get_membership_repository),
) -> PersonService:
    # Service composes two repositories — it joins Person + Membership itself.
    return PersonService(repository, membership_repository)


def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_auth_service(
    repository: UserRepository = Depends(get_user_repository),
) -> AuthService:
    return AuthService(repository)


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

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise get_credential_exception() from None

    user = auth_service.get_user_by_id(user_id)
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
