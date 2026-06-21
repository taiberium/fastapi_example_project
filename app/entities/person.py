from sqlmodel import Field

from app.entities.base import Base


class Person(Base, table=True):
    __tablename__ = "person"

    id: int = Field(default=None, primary_key=True)
    name: str
    age: int
    email: str = Field(unique=True)
