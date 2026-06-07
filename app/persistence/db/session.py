from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.core.settings import settings


def get_engine(database_url: str, echo: bool = False) -> Engine:
    return create_engine(database_url, echo=echo)


def get_local_session(database_url: str, echo: bool = False) -> sessionmaker:
    return sessionmaker(
        autocommit=False, autoflush=False, bind=get_engine(database_url, echo)
    )


SQLALCHEMY_DATABASE_URL = settings.database_url
engine = get_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
