"""Celery-side dependency injection — declare deps exactly like a FastAPI route.

`@inject` reads a task's `Annotated[X, Depends(X)]` parameters, opens the
`session_scope` unit of work, resolves each dependency through the SAME FastAPI
DI (`resolve`), and passes them in — so the task body just uses the service.
Message arguments (no `Depends`) pass through from Celery untouched.
"""

import inspect
from collections.abc import Callable
from functools import wraps
from typing import Annotated, Any, get_args, get_origin

from fastapi.params import Depends as DependsParam

from app.core.di import resolve
from app.outbound.persistence.db.session import session_scope


def _dependency_of(annotation: Any) -> Callable[..., Any] | None:
    """Return the dependency from `Annotated[T, Depends(dep)]`, else None."""
    if get_origin(annotation) is not Annotated:
        return None
    declared_type, *metadata = get_args(annotation)
    for meta in metadata:
        if isinstance(meta, DependsParam):
            return meta.dependency or declared_type
    return None


def inject(fn: Callable[..., Any]) -> Callable[..., Any]:
    deps = {
        name: dep
        for name, param in inspect.signature(fn).parameters.items()
        if (dep := _dependency_of(param.annotation)) is not None
    }

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with session_scope() as db:
            for name, dep in deps.items():
                kwargs[name] = resolve(dep, db)
            return fn(*args, **kwargs)

    return wrapper
