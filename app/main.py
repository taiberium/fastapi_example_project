from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.person import router as person_router
from app.core.exceptions import AlreadyExistsError
from app.core.logging import configure_logging, get_logger
from app.core.settings import settings

log = get_logger(__name__)


def create_app() -> FastAPI:
    # Schema is owned by Alembic migrations (`alembic upgrade head`), NOT created here.
    configure_logging()
    app = FastAPI(title=settings.app_title)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AlreadyExistsError)
    async def _already_exists_handler(
        _: Request, exc: AlreadyExistsError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "Resource already exists"},
        )

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(person_router)
    log.info("application started: %s", settings.app_title)
    return app


app = create_app()
