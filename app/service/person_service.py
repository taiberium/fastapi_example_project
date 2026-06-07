from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.config.logging import get_logger
from app.entities.person import Person
from app.persistence.repository.person_repository import person_repository

log = get_logger(__name__)


class PersonService:
    """Business logic for persons. Operates on entities — schemas never reach this layer."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repository = person_repository

    def create(self, person: Person) -> Person:
        log.info("creating person email=%s", person.email)
        return self._repository.create(self._session, person)

    def find_younger_than(
        self, age: int, skip: int = 0, limit: int = 100
    ) -> Sequence[Person]:
        log.info("finding persons younger than %s (skip=%s limit=%s)", age, skip, limit)
        return self._repository.get_many(
            self._session, Person.age < age, skip=skip, limit=limit
        )
