from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.db.base_class import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    google_sub: Mapped[str] = mapped_column(unique=True, index=True)
    full_name: Mapped[str] = mapped_column(default="")
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)
