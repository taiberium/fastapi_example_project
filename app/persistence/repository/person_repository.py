from sqlalchemy.orm import Session

from app.entities.person import Person
from app.persistence.repository.base import CRUDRepository


class PersonRepository(CRUDRepository[Person]):
    """Per-request data access for Person.

    The reason this per-entity subclass exists (instead of using the generic
    CRUDRepository directly) is to host entity-specific queries: the generic base
    only knows expression-based lookups, so domain queries like "find by email"
    live here, next to the Person model, with a clear typed name.
    """

    def __init__(self, session: Session) -> None:
        super().__init__(Person, session)

    def find_by_email(self, email: str) -> Person | None:
        return self.get_one(Person.email == email)
