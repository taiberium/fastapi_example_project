from sqlmodel import Field

from app.entities.base import Base


class Membership(Base, table=True):
    __tablename__ = "membership"

    id: int = Field(default=None, primary_key=True)
    person_id: int = Field(foreign_key="person.id", unique=True, index=True)
    tier: str = Field(default="free")  # free | pro | enterprise
    is_active: bool = Field(default=True)
