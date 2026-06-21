from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, create_engine

from app.core.settings import settings


def get_engine(database_url: str, echo: bool | None = None) -> Engine:
    """Build the engine. QueuePool tuning is applied only for real servers
    (Postgres/MySQL); sqlite gets just check_same_thread + pre_ping/recycle."""
    echo = settings.db_echo if echo is None else echo
    kwargs: dict = {
        "echo": echo,
        "pool_pre_ping": settings.db_pool_pre_ping,
        "pool_recycle": settings.db_pool_recycle,
    }
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs.update(
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_reset_on_return="rollback",  # clean transaction state on return
            pool_use_lifo=True,  # reuse hot connections, let idle ones expire
        )
    return create_engine(database_url, **kwargs)


SQLALCHEMY_DATABASE_URL = settings.database_url
engine = get_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # keep entities readable after the UoW commit (no reload)
    bind=engine,
    class_=Session,
)


@contextmanager
def session_scope(session_factory: sessionmaker = SessionLocal) -> Iterator[Session]:
    """Session lifecycle for non-HTTP entry points (Celery tasks): open, roll back
    on error, always close. Commits happen at the repository (CRUD) level — the
    same as the HTTP `get_db`. `session_factory` is injectable for tests."""
    db = session_factory()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
