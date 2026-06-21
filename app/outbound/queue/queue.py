from typing import Protocol


class JobQueue(Protocol):
    """Outbound port: dispatch background work.

    The application (services) depends on this abstraction, never on a broker, so
    the adapter (Celery -> RabbitMQ -> ...) can be swapped without touching the
    core. Add a method per job the app can enqueue.
    """

    def enqueue_recompute_overview(self, person_id: int) -> None: ...


def get_job_queue() -> JobQueue:
    # The single place that binds the port to a concrete adapter — swap here.
    from app.outbound.queue.celery_queue import CeleryJobQueue

    return CeleryJobQueue()
