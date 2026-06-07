from fastapi import FastAPI

from app.api.routes.person import router as person_router
from app.config.logging import configure_logging, get_logger
from app.config.settings import settings
from app.persistence.db.base_class import Base
from app.persistence.db.session import engine
from app.entities import person  # noqa: F401  registers the Person table on Base

log = get_logger(__name__)


def create_app() -> FastAPI:
    configure_logging()
    Base.metadata.create_all(bind=engine)
    app = FastAPI(title=settings.app_title)
    app.include_router(person_router)
    log.info("application started: %s", settings.app_title)
    return app


app = create_app()
