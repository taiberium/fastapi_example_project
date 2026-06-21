from fastapi import Request
from sqlmodel import Session


def get_db(request: Request) -> Session:
    """Return the request-scoped session. Its lifecycle (open/commit/rollback/
    close) is owned by TransactionMiddleware — this just hands it to repositories."""
    return request.state.db
