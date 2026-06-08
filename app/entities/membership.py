from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.db.base_class import Base


class Membership(Base):
    __tablename__ = "membership"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    person_id: Mapped[int] = mapped_column(
        ForeignKey("person.id"), unique=True, index=True
    )
    tier: Mapped[str] = mapped_column(default="free")  # free | pro | enterprise
    is_active: Mapped[bool] = mapped_column(default=True)
