"""Background worker that executes queued task jobs (ADR-016).

Run with ``python -m app.worker``. Several replicas may run concurrently: jobs are
claimed with ``SELECT ... FOR UPDATE SKIP LOCKED`` and protected by a renewable lease.
"""

import logging
import os
import signal
import socket
import threading
import time
from collections.abc import Callable
from types import FrameType
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import configure_logging, log_context
from app.db.models import TaskJobRecord, TaskRecord
from app.db.session import new_session
from app.models.contracts import TaskStatus, utc_now
from app.orchestration.checkpoint import close_checkpointer, init_checkpointer
from app.services.audit import record_event
from app.services.github_issues import run_github_issue_analysis
from app.services.jobs import (
    JobKind,
    JobStatus,
    claim_next_job,
    finish_job,
    reap_expired_jobs,
    renew_lease,
)
from app.services.pull_request_reviews import run_pull_request_review
from app.services.tasks import run_human_review_resume, run_task_workflow

logger = logging.getLogger("steh.worker")

SessionFactory = Callable[[], Session]
JobHandler = Callable[[Session, TaskJobRecord], object]

HANDLERS: dict[str, JobHandler] = {
    JobKind.EXECUTE_TASK: lambda db, job: run_task_workflow(db, job.task_id),
    JobKind.ANALYZE_GITHUB_ISSUE: lambda db, job: run_github_issue_analysis(db, job.task_id),
    JobKind.REVIEW_PULL_REQUEST: lambda db, job: run_pull_request_review(db, job.task_id),
    JobKind.RESUME_HUMAN_REVIEW: lambda db, job: run_human_review_resume(
        db, job.task_id, job.payload
    ),
}


def default_worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


class _LeaseKeeper(threading.Thread):
    """Renews the job lease every lease/3 seconds using its own database session."""

    def __init__(
        self,
        job_id: UUID,
        worker_id: str,
        lease_seconds: int,
        session_factory: SessionFactory,
    ) -> None:
        super().__init__(name=f"lease-{job_id}", daemon=True)
        self._job_id = job_id
        self._worker_id = worker_id
        self._lease_seconds = lease_seconds
        self._session_factory = session_factory
        self._stopped = threading.Event()

    def run(self) -> None:
        # Threads do not inherit context variables, so bind the job id here.
        with log_context(job_id=self._job_id):
            self._renew_until_stopped()

    def _renew_until_stopped(self) -> None:
        interval = max(1.0, self._lease_seconds / 3)
        while not self._stopped.wait(interval):
            try:
                with self._session_factory() as db:
                    renew_lease(db, self._job_id, self._worker_id, self._lease_seconds)
            except Exception:
                logger.exception(
                    "lease_renewal_failed",
                    extra={"event": "lease_renewal_failed"},
                )

    def stop(self) -> None:
        self._stopped.set()
        self.join(timeout=5)


def _mark_task_failed(db: Session, job: TaskJobRecord, error_type: str) -> None:
    task = db.get(TaskRecord, job.task_id)
    if task is None or task.status == TaskStatus.FAILED:
        return
    task.status = TaskStatus.FAILED
    task.updated_at = utc_now()
    db.commit()
    record_event(
        db,
        task.task_id,
        task.trace_id,
        "TASK_FAILED",
        "worker",
        {"job_id": str(job.job_id), "kind": job.kind, "error_type": error_type},
    )


def process_job(
    db: Session,
    job: TaskJobRecord,
    worker_id: str,
    lease_seconds: int,
    session_factory: SessionFactory = new_session,
) -> JobStatus:
    job_id, task_id = job.job_id, job.task_id
    task = db.get(TaskRecord, task_id)
    trace_id = task.trace_id if task is not None else None

    with log_context(task_id=task_id, trace_id=trace_id, job_id=job_id):
        return _run_job(db, job, worker_id, lease_seconds, session_factory)


def _run_job(
    db: Session,
    job: TaskJobRecord,
    worker_id: str,
    lease_seconds: int,
    session_factory: SessionFactory,
) -> JobStatus:
    job_id, kind = job.job_id, job.kind
    log_extra = {"agent": "worker", "node": kind}
    started = time.perf_counter()

    keeper = _LeaseKeeper(job_id, worker_id, lease_seconds, session_factory)
    keeper.start()
    try:
        handler = HANDLERS.get(kind)
        if handler is None:
            raise ValueError(f"Unknown job kind: {kind}")
        handler(db, job)
    except Exception as exc:
        db.rollback()
        logger.exception(
            "job_failed",
            extra={
                **log_extra,
                "event": "job_failed",
                "status": JobStatus.FAILED,
                "error_type": type(exc).__name__,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        claimed = db.get(TaskJobRecord, job_id)
        if claimed is not None:
            _mark_task_failed(db, claimed, type(exc).__name__)
            finish_job(db, claimed, JobStatus.FAILED, type(exc).__name__)
        return JobStatus.FAILED
    finally:
        keeper.stop()

    finish_job(db, job, JobStatus.SUCCEEDED)
    logger.info(
        "job_succeeded",
        extra={
            **log_extra,
            "event": "job_succeeded",
            "status": JobStatus.SUCCEEDED,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        },
    )
    return JobStatus.SUCCEEDED


def run_once(
    worker_id: str | None = None,
    session_factory: SessionFactory = new_session,
    lease_seconds: int | None = None,
) -> bool:
    """Process at most one job. Returns False when the queue is empty."""
    settings = get_settings()
    worker_id = worker_id or default_worker_id()
    lease = lease_seconds or settings.worker_lease_seconds

    with session_factory() as db:
        reap_expired_jobs(db)
        job = claim_next_job(db, worker_id, lease)
        if job is None:
            return False
        process_job(db, job, worker_id, lease, session_factory)
        return True


def run_forever(poll_interval: float | None = None) -> None:
    settings = get_settings()
    worker_id = default_worker_id()
    interval = poll_interval or settings.worker_poll_interval_seconds
    stopping = threading.Event()

    def _request_stop(signum: int, _frame: FrameType | None) -> None:
        logger.info("worker_stopping", extra={"event": "worker_stopping"})
        stopping.set()

    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)

    logger.info("worker_started", extra={"event": "worker_started", "agent": worker_id})
    while not stopping.is_set():
        try:
            worked = run_once(worker_id)
        except Exception:
            logger.exception("worker_iteration_failed", extra={"event": "worker_iteration_failed"})
            worked = False
        if not worked:
            stopping.wait(interval)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    init_checkpointer()
    try:
        run_forever()
    finally:
        close_checkpointer()


if __name__ == "__main__":
    main()
