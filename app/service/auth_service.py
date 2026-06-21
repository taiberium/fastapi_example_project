from typing import Annotated

from fastapi import Depends

from app.core import security
from app.core.exceptions import AlreadyExistsError
from app.core.logging import get_logger
from app.entities.user import User
from app.persistence.repository.user_repository import UserRepository

log = get_logger(__name__)


class AuthService:
    """Authentication business logic: Google sign-in -> app session token."""

    def __init__(self, repository: Annotated[UserRepository, Depends(UserRepository)]):
        self._repository = repository

    def login_with_google(self, id_token: str) -> tuple[User, str] | None:
        """Verify a Google ID token, provision the user, return (user, app JWT).

        Returns None if the token is invalid, unverified, or missing required claims.
        """
        claims = security.verify_google_id_token(id_token)
        if claims is None or not self._claims_are_complete(claims):
            log.info("google login rejected: invalid/unverified/incomplete token")
            return None

        user = self._get_or_create(claims)  # committed by TransactionMiddleware
        token = security.create_access_token(subject=user.id)
        log.info("google login ok: user_id=%s", user.id)
        return user, token

    def get_user_by_id(self, user_id: int) -> User | None:
        return self._repository.get_one(User.id == user_id)

    @staticmethod
    def _claims_are_complete(claims: dict) -> bool:
        # Require the identifying claims plus a verified email, so we never index a
        # missing key and never trust an unverified Google email.
        return bool(
            claims.get("sub") and claims.get("email") and claims.get("email_verified")
        )

    def _get_or_create(self, claims: dict) -> User:
        user = self._repository.get_one(User.google_sub == claims["sub"])
        if user is not None:
            return user
        # First sign-in: provision a user from the verified Google identity.
        new_user = User(
            email=claims["email"],
            google_sub=claims["sub"],
            full_name=claims.get("name", ""),
        )
        try:
            return self._repository.create(new_user)
        except AlreadyExistsError:
            # A concurrent first sign-in won the race; the session was rolled back,
            # so re-fetch the now-existing user by the same identity.
            existing = self._repository.get_one(User.google_sub == claims["sub"])
            if existing is None:
                raise  # genuine conflict (e.g. email already used by another account)
            return existing
