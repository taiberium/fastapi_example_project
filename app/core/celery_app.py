from celery import Celery

from app.core.settings import settings

# Shared Celery instance: the producer (outbound/queue) sends tasks on it and the
# worker (inbound/celery) runs the tasks it discovers via `include`.
celery_app = Celery(
    "app",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend or None,
    include=["app.inbound.celery.person_tasks"],
)

# Reliability + safety. acks_late + reject_on_worker_lost => a task whose worker dies
# mid-run is redelivered instead of acknowledged-and-lost; prefetch=1 keeps only one
# unacked task per worker so that redelivery is precise. json-only payloads block a
# pickle decode of stale objects (we only ever send primitive ids anyway).
celery_app.conf.update(
    task_acks_late=settings.celery_task_acks_late,
    task_reject_on_worker_lost=settings.celery_task_reject_on_worker_lost,
    worker_prefetch_multiplier=settings.celery_worker_prefetch_multiplier,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)
