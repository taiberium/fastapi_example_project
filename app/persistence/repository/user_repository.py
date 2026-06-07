from sqlalchemy.orm import Session

from app.entities.user import User
from app.persistence.repository.base import CRUDRepository


class UserRepository(CRUDRepository[User]):
    """Per-request data access for User. Add User-specific queries here."""

    def __init__(self, session: Session) -> None:
        super().__init__(User, session)
