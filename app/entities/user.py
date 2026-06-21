from sqlmodel import Field

from app.entities.base import Base


class User(Base, table=True):
    __tablename__ = "user"

    id: int = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    google_sub: str = Field(unique=True, index=True)
    full_name: str = Field(default="")
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
