from collections.abc import Generator

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.persistence.db.session import SessionLocal

log = get_logger(__name__)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session, closing it when the request finishes."""
    log.debug("opening database session")
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        log.debug("closing database session")
        db.close()
