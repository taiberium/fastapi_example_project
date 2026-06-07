"""Generic CRUD (Create, Read, Update, Delete) repository for ORM models.

Works with ORM entities only — no Pydantic/schema coupling. Mapping from API
schemas to entities is the service layer's job. The repository holds the
per-request Session, so callers above it never touch SQLAlchemy directly.
"""

from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AlreadyExistsError
from app.core.logging import get_logger

log = get_logger(__name__)

ORMModel = TypeVar("ORMModel")


class CRUDRepository(Generic[ORMModel]):
    """CRUD operations bound to a single ORM model and a Session.

    Constructed per request (the Session is request-scoped) — not a singleton.
    """

    def __init__(self, model: type[ORMModel], session: Session) -> None:
        self._model = model
        self._session = session

    def get_one(self, *args, **kwargs) -> ORMModel | None:
        # *args -> filter(...) for expressions, **kwargs -> filter_by(...) for equality.
        return self._session.query(self._model).filter(*args).filter_by(**kwargs).first()

    def get_many(
        self, *args, skip: int = 0, limit: int = 100, **kwargs
    ) -> Sequence[ORMModel]:
        return (
            self._session.query(self._model)
            .filter(*args)
            .filter_by(**kwargs)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(self, db_obj: ORMModel) -> ORMModel:
        log.debug("creating %s", self._model.__name__)
        self._session.add(db_obj)
        self._commit()
        self._session.refresh(db_obj)
        return db_obj

    def update(self, db_obj: ORMModel, values: dict[str, Any]) -> ORMModel:
        log.debug("updating %s with %s", self._model.__name__, values)
        for field, value in values.items():
            setattr(db_obj, field, value)
        self._session.add(db_obj)
        self._commit()
        self._session.refresh(db_obj)
        return db_obj

    def delete(self, db_obj: ORMModel) -> ORMModel:
        log.debug("deleting %s", self._model.__name__)
        self._session.delete(db_obj)
        self._commit()
        return db_obj

    def _commit(self) -> None:
        # Roll back on a failed commit so the session stays usable; surface unique
        # violations as a domain error instead of leaking IntegrityError upward.
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise AlreadyExistsError(str(exc.orig)) from exc
