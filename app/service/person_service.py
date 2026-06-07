from collections.abc import Sequence

from app.core.logging import get_logger
from app.entities.person import Person
from app.persistence.repository.person_repository import PersonRepository

log = get_logger(__name__)


class PersonService:
    """Business logic for persons. Operates on entities — no Session, no schemas here."""

    def __init__(self, repository: PersonRepository) -> None:
        self._repository = repository

    def create(self, person: Person) -> Person:
        log.info("creating person email=%s", person.email)
        return self._repository.create(person)

    def find_younger_than(
        self, age: int, skip: int = 0, limit: int = 100
    ) -> Sequence[Person]:
        log.info("finding persons younger than %s (skip=%s limit=%s)", age, skip, limit)
        return self._repository.get_many(Person.age < age, skip=skip, limit=limit)

    def find_by_email(self, email: str) -> Person | None:
        log.info("finding person by email=%s", email)
        return self._repository.find_by_email(email)
