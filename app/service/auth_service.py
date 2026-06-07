from sqlalchemy.orm import Session

from app.core import security
from app.core.logging import get_logger
from app.entities.user import User
from app.persistence.repository.user_repository import user_repository

log = get_logger(__name__)


class AuthService:
    """Authentication business logic: Google sign-in -> app session token."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = user_repository

    def login_with_google(self, id_token: str) -> tuple[User, str] | None:
        """Verify a Google ID token, provision the user, return (user, app JWT).

        Returns None if the Google token is invalid.
        """
        claims = security.verify_google_id_token(id_token)
        if claims is None:
            log.info("google login rejected: invalid id token")
            return None

        user = self._get_or_create(claims)
        token = security.create_access_token(subject=user.id)
        log.info("google login ok: user_id=%s", user.id)
        return user, token

    def get_user_by_id(self, user_id: int) -> User | None:
        return self._repository.get_one(self._session, User.id == user_id)

    def _get_or_create(self, claims: dict) -> User:
        user = self._repository.get_one(
            self._session, User.google_sub == claims["sub"]
        )
        if user is not None:
            return user
        # First sign-in: provision a user from the verified Google identity.
        user = User(
            email=claims["email"],
            google_sub=claims["sub"],
            full_name=claims.get("name", ""),
        )
        return self._repository.create(self._session, user)
