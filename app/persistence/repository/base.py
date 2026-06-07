"""Generic CRUD (Create, Read, Update, Delete) repository for ORM models.

Works with ORM entities only — no Pydantic/schema coupling. Mapping from API
schemas to entities is the service layer's job.
"""

from typing import Any, Generic, Optional, Sequence, Type, TypeVar

from sqlalchemy.orm import Session

from app.core.logging import get_logger

log = get_logger(__name__)

ORMModel = TypeVar("ORMModel")


class CRUDRepository(Generic[ORMModel]):
    """Stateless CRUD operations bound to a single ORM model.

    The session is passed per call so one instance can be reused as a
    module-level singleton (see person_repository.py).
    """

    def __init__(self, model: Type[ORMModel]) -> None:
        self._model = model

    def get_one(self, db: Session, *args, **kwargs) -> Optional[ORMModel]:
        # *args -> filter(...) for expressions, **kwargs -> filter_by(...) for equality.
        return db.query(self._model).filter(*args).filter_by(**kwargs).first()

    def get_many(
        self, db: Session, *args, skip: int = 0, limit: int = 100, **kwargs
    ) -> Sequence[ORMModel]:
        return (
            db.query(self._model)
            .filter(*args)
            .filter_by(**kwargs)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(self, db: Session, db_obj: ORMModel) -> ORMModel:
        log.debug("creating %s", self._model.__name__)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, db: Session, db_obj: ORMModel, values: dict[str, Any]
    ) -> ORMModel:
        log.debug("updating %s with %s", self._model.__name__, values)
        for field, value in values.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, db_obj: ORMModel) -> ORMModel:
        log.debug("deleting %s", self._model.__name__)
        db.delete(db_obj)
        db.commit()
        return db_obj
