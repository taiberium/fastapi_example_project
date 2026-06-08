from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PersonCreate(BaseModel):
    name: str
    age: int = Field(ge=0)
    email: EmailStr  # validates email format at the API boundary


class PersonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    age: int
    email: str


class MembershipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tier: str
    is_active: bool


class PersonOverviewRead(BaseModel):
    # Person fields + the combined membership + the service-derived flag.
    id: int
    name: str
    age: int
    email: str
    is_premium: bool
    membership: MembershipRead | None
