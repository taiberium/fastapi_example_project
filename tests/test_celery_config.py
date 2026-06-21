from app.core.celery_app import celery_app
from app.core.settings import settings
from app.core.task_names import RECOMPUTE_OVERVIEW
from app.inbound.celery import person_tasks  # noqa: F401  registers the task


def test_acks_late_so_a_dying_worker_redelivers_instead_of_losing_the_task():
    # Default Celery acks on receipt (before run) -> a crash mid-task loses it.
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.task_reject_on_worker_lost is True


def test_one_unacked_task_per_worker_so_redelivery_is_precise():
    assert celery_app.conf.worker_prefetch_multiplier == 1


def test_json_only_payloads_block_pickle_decode_of_old_objects():
    assert celery_app.conf.accept_content == ["json"]
    assert celery_app.conf.task_serializer == "json"


def test_recompute_overview_retries_are_bounded():
    task = celery_app.tasks[RECOMPUTE_OVERVIEW]
    assert task.max_retries == settings.celery_task_max_retries
