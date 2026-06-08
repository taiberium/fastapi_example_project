from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.entities.membership import Membership
from app.entities.person import Person
from app.persistence.repository.membership_repository import MembershipRepository
from app.persistence.repository.person_repository import PersonRepository
from app.service.person_service import PersonService


def _service(
    db_session: Session,
) -> tuple[PersonService, PersonRepository, MembershipRepository]:
    persons = PersonRepository(db_session)
    memberships = MembershipRepository(db_session)
    return PersonService(persons, memberships), persons, memberships


# --- service-level join (the point of the feature) ---


def test_overview_combines_person_with_active_pro_membership(db_session: Session) -> None:
    service, persons, memberships = _service(db_session)
    person = persons.create(Person(name="Pro", age=30, email="pro@example.com"))
    memberships.create(Membership(person_id=person.id, tier="pro", is_active=True))

    overview = service.get_overview(person.id)

    assert overview is not None
    assert overview.person.id == person.id
    assert overview.membership is not None
    assert overview.membership.tier == "pro"
    assert overview.is_premium is True


def test_overview_not_premium_without_membership(db_session: Session) -> None:
    service, persons, _ = _service(db_session)
    person = persons.create(Person(name="Free", age=25, email="free@example.com"))

    overview = service.get_overview(person.id)

    assert overview is not None
    assert overview.membership is None
    assert overview.is_premium is False


def test_overview_not_premium_when_membership_inactive(db_session: Session) -> None:
    service, persons, memberships = _service(db_session)
    person = persons.create(Person(name="Lapsed", age=40, email="lapsed@example.com"))
    memberships.create(Membership(person_id=person.id, tier="pro", is_active=False))

    overview = service.get_overview(person.id)

    assert overview is not None
    assert overview.is_premium is False


def test_overview_returns_none_for_missing_person(db_session: Session) -> None:
    service, _, _ = _service(db_session)
    assert service.get_overview(9999) is None


def test_membership_repository_find_by_person_id(db_session: Session) -> None:
    persons = PersonRepository(db_session)
    memberships = MembershipRepository(db_session)
    person = persons.create(Person(name="M", age=20, email="m@example.com"))
    memberships.create(Membership(person_id=person.id, tier="free", is_active=True))

    found = memberships.find_by_person_id(person.id)

    assert found is not None
    assert found.person_id == person.id


# --- route ---


def test_overview_endpoint_person_without_membership(client: TestClient) -> None:
    pid = client.post(
        "/persons", json={"name": "Solo", "age": 22, "email": "solo@example.com"}
    ).json()["id"]

    response = client.get(f"/persons/{pid}/overview")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == pid
    assert body["is_premium"] is False
    assert body["membership"] is None


def test_overview_endpoint_404_for_missing_person(client: TestClient) -> None:
    assert client.get("/persons/9999/overview").status_code == 404
