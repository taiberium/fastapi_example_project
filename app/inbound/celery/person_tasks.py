from app.core.celery_app import celery_app
from app.core.logging import get_logger
from app.core.task_names import RECOMPUTE_OVERVIEW
from app.outbound.persistence.db.session import session_scope
from app.outbound.persistence.repository.membership_repository import (
    MembershipRepository,
)
from app.outbound.persistence.repository.person_repository import PersonRepository
from app.outbound.queue.queue import get_job_queue
from app.service.person_service import PersonService

log = get_logger(__name__)


@celery_app.task(name=RECOMPUTE_OVERVIEW)
def recompute_overview(person_id: int) -> None:
    # Inbound adapter (broker side): open the worker's unit of work, build the
    # service, delegate. Thin, like an HTTP route — business logic stays in service.
    with session_scope() as db:
        service = PersonService(
            PersonRepository(db), MembershipRepository(db), get_job_queue()
        )
        overview = service.get_overview(person_id)
    log.info(
        "recomputed overview person_id=%s premium=%s",
        person_id,
        overview.is_premium if overview else None,
    )
