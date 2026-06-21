from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from app.entities.user import User
from app.persistence.db.db import get_db
from app.persistence.repository.crud_repository import CRUDRepository


class UserRepository(CRUDRepository[User]):
    """Per-request data access for User (self-wires the request Session)."""

    def __init__(self, session: Annotated[Session, Depends(get_db)]):
        super().__init__(User, session)
