from sqlalchemy.orm import Session

from app.entities.membership import Membership
from app.persistence.repository.base import CRUDRepository


class MembershipRepository(CRUDRepository[Membership]):
    """Per-request data access for Membership."""

    def __init__(self, session: Session) -> None:
        super().__init__(Membership, session)

    def find_by_person_id(self, person_id: int) -> Membership | None:
        return self.get_one(Membership.person_id == person_id)
