from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from app.core.logging import get_logger
from app.entities.membership import Membership
from app.entities.person import Person
from app.outbound.channel.channel import MessageChannel
from app.outbound.persistence.repository.membership_repository import MembershipRepository
from app.outbound.persistence.repository.person_repository import PersonRepository
from app.outbound.queue.queue import JobQueue, get_job_queue

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
        queue: Annotated[JobQueue, Depends(get_job_queue)],
    ):
        self._repository = repository
        self._memberships = membership_repository
        self._queue = queue

    def create(self, person: Person) -> Person:
        # The repository commits the write (CRUD level).
        log.info("creating person email=%s", person.email)
        created = self._repository.create(person)
        # Business decision to do follow-up work async -> outbound queue port.
        self._queue.enqueue_recompute_overview(created.id)
        return created

    def find_younger_than(
        self, age: int, skip: int = 0, limit: int = 100
    ) -> Sequence[Person]:
        log.info("finding persons younger than %s (skip=%s limit=%s)", age, skip, limit)
        return self._repository.get_many(Person.age < age, skip=skip, limit=limit)

    def find_by_email(self, email: str) -> Person | None:
        log.info("finding person by email=%s", email)
        return self._repository.find_by_email(email)

    async def push_overview(self, person_id: int, channel: MessageChannel) -> None:
        # Input -> service -> output: the SERVICE drives the send through the port.
        overview = self.get_overview(person_id)
        if overview is None:
            await channel.send({"error": "not found"})
        else:
            await channel.send(
                {
                    "id": overview.person.id,
                    "name": overview.person.name,
                    "is_premium": overview.is_premium,
                }
            )

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
