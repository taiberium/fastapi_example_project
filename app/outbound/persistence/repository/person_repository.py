from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.entities.person import Person
from app.outbound.persistence.db.db import get_db
from app.outbound.persistence.repository.crud_repository import CRUDRepository


class PersonRepository(CRUDRepository[Person]):
    """Per-request data access for Person.

    The reason this per-entity subclass exists (instead of using the generic
    CRUDRepository directly) is to host entity-specific queries: the generic base
    only knows expression-based lookups, so domain queries like "find by email"
    live here, next to the Person model, with a clear typed name.

    Self-wiring: the request-scoped Session is injected straight into the
    constructor, so the class is usable as a FastAPI dependency on its own.
    """

    def __init__(self, session: Annotated[Session, Depends(get_db)]):
        super().__init__(Person, session)

    def find_by_email(self, email: str) -> Person | None:
        return self.get_one(Person.email == email)
