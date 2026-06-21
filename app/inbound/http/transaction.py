from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.logging import get_logger

log = get_logger(__name__)


class TransactionMiddleware(BaseHTTPMiddleware):
    """One DB transaction per request — the unit of work.

    Opens a session, exposes it via `request.state.db` (which `get_db` hands to
    repositories), then on the way out commits a successful (<400) response, rolls
    back otherwise, and always closes. The commit runs here, inside request
    handling, so a failed commit surfaces as a real HTTP 500 instead of a response
    that already claimed success. Nothing in routes/services has to remember to
    commit, so multi-write use-cases are atomic by default — you can't forget it.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        db = request.app.state.db_sessionmaker()
        request.state.db = db
        try:
            response = await call_next(request)
            if response.status_code < 400:
                db.commit()
            else:
                db.rollback()
            return response
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
