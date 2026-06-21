from sqlmodel import Session

from app.entities.person import Person
from app.persistence.repository.person_repository import PersonRepository


def test_find_by_email_returns_matching_person(db_session: Session) -> None:
    repo = PersonRepository(db_session)
    repo.create(Person(name="Alice", age=20, email="alice@example.com"))

    found = repo.find_by_email("alice@example.com")

    assert found is not None
    assert found.name == "Alice"


def test_find_by_email_returns_none_when_absent(db_session: Session) -> None:
    repo = PersonRepository(db_session)

    assert repo.find_by_email("missing@example.com") is None
