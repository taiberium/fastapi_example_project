"""Reuse FastAPI's dependency injection outside an HTTP request.

FastAPI resolves `Depends(...)` graphs only inside a request. This runs FastAPI's
own resolver (`solve_dependencies`) against a synthetic request, overriding
`get_db` with the caller's session — so the SAME `Annotated[X, Depends(X)]`
self-wiring used by routes also wires services for Celery tasks, CLI, scripts.
One DI mechanism, everywhere.
"""

import asyncio
from collections.abc import Callable
from contextlib import AsyncExitStack
from typing import Any, TypeVar

from fastapi import Request
from fastapi.dependencies.utils import get_dependant, solve_dependencies
from sqlmodel import Session

from app.outbound.persistence.db.db import get_db

T = TypeVar("T")


class _Overrides:
    """Minimal `dependency_overrides_provider` for solve_dependencies."""

    def __init__(self, mapping: dict[Callable[..., Any], Callable[..., Any]]):
        self.dependency_overrides = mapping


async def _aresolve(call: Callable[..., T], db: Session, extra: Any) -> T:
    overrides: dict[Callable[..., Any], Callable[..., Any]] = {get_db: lambda: db}
    if extra:
        overrides.update(extra)
    async with AsyncExitStack() as stack:
        scope = {
            "type": "http",
            "headers": [],
            "query_string": b"",
            "path": "/",
            "method": "GET",
            "fastapi_astack": stack,
        }
        dependant = get_dependant(path="", call=call)
        values, errors, *_ = await solve_dependencies(
            request=Request(scope),
            dependant=dependant,
            dependency_overrides_provider=_Overrides(overrides),
        )
        if errors:
            raise RuntimeError(f"dependency resolution failed: {errors}")
        assert dependant.call is not None
        return dependant.call(**values)


def resolve(call: Callable[..., T], db: Session, extra: Any = None) -> T:
    """Build `call` (a service/class) by resolving its FastAPI `Depends` graph
    against `db` (injected in place of `get_db`). Used by non-HTTP entry points
    (Celery tasks) so they get the same fully-wired services as routes — never
    hand-wiring repositories."""
    return asyncio.run(_aresolve(call, db, extra))
