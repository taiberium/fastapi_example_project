from typing import Annotated

from fastapi import Depends

from app.core.celery_app import celery_app
from app.core.logging import get_logger
from app.core.settings import settings
from app.core.task_names import RECOMPUTE_OVERVIEW
from app.inbound.celery.base import inject
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
@inject
def recompute_overview(
    person_id: int,
    service: Annotated[PersonService, Depends(PersonService)],
) -> None:
    # Same dependency signature as a FastAPI route; @inject wires it. Just use it.
    overview = service.get_overview(person_id)
    log.info(
        "recomputed overview person_id=%s premium=%s",
        person_id,
        overview.is_premium if overview else None,
    )
