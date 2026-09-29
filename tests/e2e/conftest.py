from collections.abc import Callable

import pytest

from app.worker import run_once

MAX_JOBS_PER_DRAIN = 50


@pytest.fixture
def drain_jobs() -> Callable[[], int]:
    """Run the worker in-process until the queue is empty (ADR-016)."""

    def drain() -> int:
        processed = 0
        while run_once(worker_id="e2e-worker"):
            processed += 1
            if processed > MAX_JOBS_PER_DRAIN:
                raise AssertionError("Task job queue did not drain.")
        return processed

    return drain
