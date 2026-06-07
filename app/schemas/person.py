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
