from app.entities.person import Person
from app.persistence.repository.base import CRUDRepository

# Module-level singleton, mirroring the gymhero `bodypart_crud = CRUDRepository(model=BodyPart)` pattern.
person_repository = CRUDRepository(model=Person)
