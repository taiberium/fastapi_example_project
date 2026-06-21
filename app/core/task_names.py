# Task names are the contract between the producer (outbound/queue) and the
# consumer (inbound/celery): send_task(...) and @celery_app.task(name=...) both
# reference these, so neither side imports the other — only this shared module.

RECOMPUTE_OVERVIEW = "person.recompute_overview"
