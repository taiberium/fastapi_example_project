from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.person import router as person_router
from app.core.logging import configure_logging, get_logger
from app.core.settings import settings

log = get_logger(__name__)


def create_app() -> FastAPI:
    # Schema is owned by Alembic migrations (`alembic upgrade head`), NOT created here.
    configure_logging()
    app = FastAPI(title=settings.app_title)
    app.include_router(auth_router)
    app.include_router(person_router)
    log.info("application started: %s", settings.app_title)
    return app


app = create_app()
