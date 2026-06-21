from app.core.celery_app import celery_app
from app.core.di import resolve
from app.core.logging import get_logger
from app.core.settings import settings
from app.core.task_names import RECOMPUTE_OVERVIEW
from app.outbound.persistence.db.session import session_scope
from app.service.person_service import PersonService

log = get_logger(__name__)


@celery_app.task(
    name=RECOMPUTE_OVERVIEW,
    # Transient failures (DB blip, etc.) retry with jittered exponential backoff up to
    # a bound; after that the task fails for good rather than looping forever.
    autoretry_for=(Exception,),
    max_retries=settings.celery_task_max_retries,
    retry_backoff=settings.celery_task_retry_backoff,
    retry_backoff_max=600,
    retry_jitter=True,
)
def recompute_overview(person_id: int) -> None:
    # Same shape as an HTTP route: open the unit of work (session_scope, like the
    # HTTP middleware), get the service via the SAME FastAPI DI (resolve, like
    # FastAPI does for routes), delegate. No repositories, no manual wiring.
    with session_scope() as db:
        service = resolve(PersonService, db)
        overview = service.get_overview(person_id)
    log.info(
        "recomputed overview person_id=%s premium=%s",
        person_id,
        overview.is_premium if overview else None,
    )
