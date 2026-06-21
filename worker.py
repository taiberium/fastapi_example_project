"""Celery worker entrypoint — analog of main.py for the API.

Run: `poetry run celery -A worker.celery_app worker -l info`
"""

from celery.signals import worker_process_init

from app.core.celery_app import celery_app
from app.outbound.persistence.db.session import engine


@worker_process_init.connect
def _reset_db_engine(**_: object) -> None:
    # Each prefork worker process forks AFTER the engine is imported, inheriting the
    # parent's pool/sockets. Drop them so the child opens its own connections.
    # close=False: don't close inherited sockets (still owned by the parent).
    engine.dispose(close=False)


__all__ = ["celery_app"]
