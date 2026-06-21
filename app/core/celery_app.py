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
