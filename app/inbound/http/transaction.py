from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.outbound.persistence.db.session import session_scope


class TransactionMiddleware(BaseHTTPMiddleware):
    """One DB transaction per request — the HTTP side of the unit of work.

    A thin shell: it runs the shared `session_scope()` around the request and
    exposes the session via `request.state.db` (which `get_db` hands to
    repositories). All transaction logic (commit on success / rollback on error /
    close) lives in `session_scope`, so HTTP and Celery manage sessions the same
    way. The commit happens here, before the response is sent, so a failed commit
    surfaces as a real HTTP 500 — and routes/services never commit themselves.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        with session_scope(request.app.state.db_sessionmaker) as db:
            request.state.db = db
            return await call_next(request)
