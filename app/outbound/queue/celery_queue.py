from app.core.celery_app import celery_app
from app.core.task_names import RECOMPUTE_OVERVIEW


class CeleryJobQueue:
    """Celery adapter for the JobQueue port. Enqueues by task NAME (no import of
    the task definition), so producer and worker stay fully decoupled."""

    def enqueue_recompute_overview(self, person_id: int) -> None:
        celery_app.send_task(RECOMPUTE_OVERVIEW, args=[person_id])
