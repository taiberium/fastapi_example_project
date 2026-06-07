from typing import Tuple

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_pagination_params, get_person_service
from app.core.exceptions import get_not_found_exception
from app.entities.person import Person
from app.schemas.person import PersonCreate, PersonRead
from app.service.person_service import PersonService

router = APIRouter(prefix="/persons", tags=["persons"])


@router.post("", response_model=PersonRead, status_code=201)
async def save(
    data: PersonCreate,
    service: PersonService = Depends(get_person_service),
) -> PersonRead:
    # schema -> entity mapping stays at the route boundary, never in the service.
    person = service.create(Person(**data.model_dump()))
    return PersonRead.model_validate(person)


@router.get("", response_model=list[PersonRead])
async def find(
    age: int = Query(ge=0),
    pagination: Tuple[int, int] = Depends(get_pagination_params),
    service: PersonService = Depends(get_person_service),
) -> list[PersonRead]:
    skip, limit = pagination
    persons = service.find_younger_than(age, skip=skip, limit=limit)
    return [PersonRead.model_validate(person) for person in persons]


@router.get("/by-email", response_model=PersonRead)
async def find_by_email(
    email: str,
    service: PersonService = Depends(get_person_service),
) -> PersonRead:
    person = service.find_by_email(email)
    if person is None:
        raise get_not_found_exception(detail="Person not found")
    return PersonRead.model_validate(person)
