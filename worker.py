"""Celery worker entrypoint — analog of main.py for the API.

Run: `poetry run celery -A worker.celery_app worker -l info`
"""

from app.core.celery_app import celery_app

__all__ = ["celery_app"]
