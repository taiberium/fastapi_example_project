"""Reuse FastAPI's dependency injection outside an HTTP request.

FastAPI resolves `Depends(...)` graphs only inside a request. This runs FastAPI's
own resolver (`solve_dependencies`) against a synthetic request whose
`state.db` carries the session — so the SAME `Annotated[X, Depends(X)]` self-wiring
used by routes also wires services for Celery tasks, CLI, scripts. One DI, everywhere.
"""

import asyncio
from collections.abc import Callable
from contextlib import AsyncExitStack
from typing import Any, TypeVar

from fastapi import Request
from fastapi.dependencies.utils import get_dependant, solve_dependencies
from sqlmodel import Session

T = TypeVar("T")


async def _aresolve(call: Callable[..., T], db: Session, overrides: Any) -> T:
    async with AsyncExitStack() as stack:
        scope = {
            "type": "http",
            "headers": [],
            "query_string": b"",
            "path": "/",
            "method": "GET",
            "fastapi_astack": stack,
        }
        request = Request(scope)
        request.state.db = db  # what get_db() returns, same as the HTTP middleware
        dependant = get_dependant(path="", call=call)
        values, errors, *_ = await solve_dependencies(
            request=request,
            dependant=dependant,
            dependency_overrides_provider=overrides,
        )
        if errors:
            raise RuntimeError(f"dependency resolution failed: {errors}")
        assert dependant.call is not None
        return dependant.call(**values)


def resolve(call: Callable[..., T], db: Session, overrides: Any = None) -> T:
    """Build `call` (a service/class) by resolving its FastAPI `Depends` graph
    against `db`. Used by non-HTTP entry points (Celery tasks) so they get the
    same fully-wired services as routes — never hand-wiring repositories."""
    return asyncio.run(_aresolve(call, db, overrides))
