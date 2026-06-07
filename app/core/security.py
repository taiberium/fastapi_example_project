"""Security primitives: app JWT session tokens + Google ID-token verification."""

from datetime import UTC, datetime, timedelta
from typing import Any

from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from jose import JWTError, jwt

from app.core.settings import settings


def create_access_token(
    subject: str | int, expires_delta: timedelta | None = None
) -> str:
    """Issue a signed JWT session token for the given subject (user id)."""
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode our own JWT. Returns the claims, or None if invalid/expired."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        return None


# Reused across logins so each request doesn't allocate a new HTTP transport/pool.
_google_request = google_requests.Request()


def verify_google_id_token(token: str) -> dict[str, Any] | None:
    """Verify a Google ID token against our client id. Returns claims or None.

    Claims include `sub` (Google account id), `email`, `name`.
    """
    try:
        return google_id_token.verify_oauth2_token(
            token, _google_request, settings.google_client_id
        )
    except (ValueError, GoogleAuthError):
        return None
