from app.entities.user import User
from app.persistence.repository.base import CRUDRepository

user_repository = CRUDRepository(model=User)
