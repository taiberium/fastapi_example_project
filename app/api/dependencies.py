from typing import Tuple

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.persistence.db.db import get_db
from app.service.person_service import PersonService


def get_pagination_params(
    skip: int = Query(0, ge=0), limit: int = Query(10, gt=0)
) -> Tuple[int, int]:
    """Return (skip, limit) pagination parameters from the query string."""
    return skip, limit


def get_person_service(db: Session = Depends(get_db)) -> PersonService:
    return PersonService(db)
