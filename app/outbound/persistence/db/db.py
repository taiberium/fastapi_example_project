from collections.abc import Generator

from sqlmodel import Session

from app.outbound.persistence.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Open a session for the request, roll back on error, always close.
    Commits happen at the repository (CRUD) level — this only owns the lifecycle."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
