"""Application-wide exceptions and HTTP exception helpers."""

from fastapi import HTTPException, status


def get_credential_exception(
    status_code: int = status.HTTP_401_UNAUTHORIZED,
    detail: str = "Could not validate credentials",
) -> HTTPException:
    """Build an auth HTTPException carrying the Bearer challenge header."""
    return HTTPException(
        status_code=status_code,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_not_found_exception(detail: str = "Resource not found") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class SQLAlchemyException(Exception):
    """Raised when a database operation fails at the persistence layer."""
