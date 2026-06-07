from pydantic import BaseModel, ConfigDict, Field


class PersonCreate(BaseModel):
    name: str
    age: int = Field(ge=0)
    email: str


class PersonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    age: int
    email: str
