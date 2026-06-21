from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from app.core.logging import get_logger
from app.entities.membership import Membership
from app.entities.person import Person
from app.persistence.repository.membership_repository import MembershipRepository
from app.persistence.repository.person_repository import PersonRepository

log = get_logger(__name__)

_PREMIUM_TIERS = {"pro", "enterprise"}


@dataclass(frozen=True)
class PersonOverview:
    """Service-level aggregate combining a Person with its Membership.

    Built by joining two repositories in the service (not a DB join), with a
    derived `is_premium` flag — the business logic that justifies this layer.
    """

    person: Person
    membership: Membership | None
    is_premium: bool


class PersonService:
    """Business logic for persons. Operates on entities — no Session, no schemas here."""

    def __init__(
        self,
        repository: Annotated[PersonRepository, Depends(PersonRepository)],
        membership_repository: Annotated[
            MembershipRepository, Depends(MembershipRepository)
        ],
    ):
        self._repository = repository
        self._memberships = membership_repository

    def create(self, person: Person) -> Person:
        # Repo flushes; the request's transaction is committed by TransactionMiddleware.
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

    def get_overview(self, person_id: int) -> PersonOverview | None:
        # Combine Person + Membership here (two repositories, one aggregate).
        person = self._repository.get_one(Person.id == person_id)
        if person is None:
            return None
        membership = self._memberships.find_by_person_id(person_id)
        is_premium = (
            membership is not None
            and membership.is_active
            and membership.tier in _PREMIUM_TIERS
        )
        log.info("person overview id=%s premium=%s", person_id, is_premium)
        return PersonOverview(person=person, membership=membership, is_premium=is_premium)
