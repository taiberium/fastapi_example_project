from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.exceptions import get_not_found_exception
from app.entities.person import Person
from app.schemas.pagination import PaginationParams
from app.schemas.person import (
    MembershipRead,
    PersonCreate,
    PersonOverviewRead,
    PersonRead,
)
from app.service.person_service import PersonService

router = APIRouter(prefix="/persons", tags=["persons"])


def get_pagination(
    skip: int = Query(0, ge=0), limit: int = Query(10, gt=0)
) -> PaginationParams:
    # Query() does the ge/gt validation (FastAPI -> 422); the schema is the DTO.
    return PaginationParams(skip=skip, limit=limit)


# Route-level DI aliases — the service self-wires its repositories.
PersonServiceDep = Annotated[PersonService, Depends(PersonService)]
Pagination = Annotated[PaginationParams, Depends(get_pagination)]


@router.post("", response_model=PersonRead, status_code=201)
async def save(
    data: PersonCreate,
    service: PersonServiceDep,
) -> PersonRead:
    # schema -> entity mapping stays at the route boundary, never in the service.
    person = service.create(Person(**data.model_dump()))
    return PersonRead.model_validate(person)


@router.get("", response_model=list[PersonRead])
async def find(
    pagination: Pagination,
    service: PersonServiceDep,
    age: int = Query(ge=0),
) -> list[PersonRead]:
    persons = service.find_younger_than(age, skip=pagination.skip, limit=pagination.limit)
    return [PersonRead.model_validate(person) for person in persons]


@router.get("/by-email", response_model=PersonRead)
async def find_by_email(
    email: str,
    service: PersonServiceDep,
) -> PersonRead:
    person = service.find_by_email(email)
    if person is None:
        raise get_not_found_exception(detail="Person not found")
    return PersonRead.model_validate(person)


@router.get("/{person_id}/overview", response_model=PersonOverviewRead)
async def overview(
    person_id: int,
    service: PersonServiceDep,
) -> PersonOverviewRead:
    result = service.get_overview(person_id)
    if result is None:
        raise get_not_found_exception(detail="Person not found")
    # Map the service aggregate -> response DTO at the route boundary.
    return PersonOverviewRead(
        id=result.person.id,
        name=result.person.name,
        age=result.person.age,
        email=result.person.email,
        is_premium=result.is_premium,
        membership=(
            MembershipRead.model_validate(result.membership)
            if result.membership is not None
            else None
        ),
    )
