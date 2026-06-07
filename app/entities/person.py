from sqlalchemy.orm import Mapped, mapped_column

from app.persistence.db.base_class import Base


class Person(Base):
    __tablename__ = "person"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column()
    age: Mapped[int] = mapped_column()
    email: Mapped[str] = mapped_column(unique=True)
