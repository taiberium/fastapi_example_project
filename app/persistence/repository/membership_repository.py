from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.entities.membership import Membership
from app.persistence.db.db import get_db
from app.persistence.repository.crud_repository import CRUDRepository


class MembershipRepository(CRUDRepository[Membership]):
    """Per-request data access for Membership (self-wires the request Session)."""

    def __init__(self, session: Annotated[Session, Depends(get_db)]):
        super().__init__(Membership, session)

    def find_by_person_id(self, person_id: int) -> Membership | None:
        return self.get_one(Membership.person_id == person_id)
