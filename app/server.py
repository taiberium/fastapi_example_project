import uvicorn

from app.core.settings import settings


def run() -> None:
    """Start the ASGI server. Auto-reload is enabled outside production."""
    uvicorn.run(
        "app.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.env in {"dev", "test"},
    )


if __name__ == "__main__":  # pragma: no cover
    run()
