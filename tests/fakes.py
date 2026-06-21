class FakeJobQueue:
    """No-op JobQueue for tests — records enqueued jobs, dispatches nothing
    (no broker needed). Satisfies the JobQueue port structurally."""

    def __init__(self) -> None:
        self.recompute_overview_calls: list[int] = []

    def enqueue_recompute_overview(self, person_id: int) -> None:
        self.recompute_overview_calls.append(person_id)
