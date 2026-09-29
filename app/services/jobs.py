import logging
from datetime import timedelta
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models import TaskJobRecord, TaskRecord
from app.models.contracts import TaskStatus, utc_now
from app.services.audit import record_event


class JobKind(StrEnum):
    EXECUTE_TASK = "EXECUTE_TASK"
    ANALYZE_GITHUB_ISSUE = "ANALYZE_GITHUB_ISSUE"
    REVIEW_PULL_REQUEST = "REVIEW_PULL_REQUEST"
    RESUME_HUMAN_REVIEW = "RESUME_HUMAN_REVIEW"


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


LEASE_EXPIRED = "LeaseExpired"

logger = logging.getLogger("steh.jobs")


def new_job(
    record: TaskRecord,
    kind: JobKind,
    payload: dict[str, Any] | None = None,
) -> TaskJobRecord:
    """Build a queued job without committing it.

    Callers add it in the same transaction that creates or claims the task, so a
    task can never be left waiting without a job. The payload must never carry raw
    client or GitHub content: workers read the sanitized snapshots already
    persisted on the task record (ADR-016).
    """
    return TaskJobRecord(
        job_id=uuid4(),
        task_id=record.task_id,
        kind=kind,
        payload=payload or {},
        status=JobStatus.QUEUED,
        attempts=0,
        created_at=utc_now(),
    )


def record_job_queued(db: Session, record: TaskRecord, job: TaskJobRecord) -> None:
    logger.info(
        "job_queued",
        extra={
            "event": "job_queued",
            "task_id": str(record.task_id),
            "trace_id": str(record.trace_id),
            "job_id": str(job.job_id),
            "node": job.kind,
        },
    )
    record_event(
        db,
        record.task_id,
        record.trace_id,
        "JOB_QUEUED",
        "api",
        {"job_id": str(job.job_id), "kind": job.kind},
    )


def enqueue_job(
    db: Session,
    record: TaskRecord,
    kind: JobKind,
    payload: dict[str, Any] | None = None,
) -> TaskJobRecord:
    """Queue a job for an already persisted task."""
    job = new_job(record, kind, payload)
    db.add(job)
    db.commit()
    record_job_queued(db, record, job)
    return job


def claim_next_job(
    db: Session,
    worker_id: str,
    lease_seconds: int,
) -> TaskJobRecord | None:
    job = db.execute(
        select(TaskJobRecord)
        .where(TaskJobRecord.status == JobStatus.QUEUED)
        .order_by(TaskJobRecord.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    ).scalar_one_or_none()

    if job is None:
        db.rollback()
        return None

    now = utc_now()
    job.status = JobStatus.RUNNING
    job.attempts += 1
    job.locked_by = worker_id
    job.started_at = now
    job.lease_expires_at = now + timedelta(seconds=lease_seconds)
    db.commit()
    return job


def renew_lease(
    db: Session,
    job_id: UUID,
    worker_id: str,
    lease_seconds: int,
) -> bool:
    result = db.execute(
        update(TaskJobRecord)
        .where(
            TaskJobRecord.job_id == job_id,
            TaskJobRecord.status == JobStatus.RUNNING,
            TaskJobRecord.locked_by == worker_id,
        )
        .values(lease_expires_at=utc_now() + timedelta(seconds=lease_seconds))
    )
    db.commit()
    return getattr(result, "rowcount", 0) == 1


def finish_job(
    db: Session,
    job: TaskJobRecord,
    status: JobStatus,
    error_type: str | None = None,
) -> None:
    job.status = status
    job.finished_at = utc_now()
    job.lease_expires_at = None
    job.last_error = error_type[:120] if error_type else None
    db.commit()


def reap_expired_jobs(db: Session) -> int:
    """Fail jobs whose worker stopped renewing the lease (ADR-016: no retries)."""
    now = utc_now()
    jobs = list(
        db.execute(
            select(TaskJobRecord)
            .where(
                TaskJobRecord.status == JobStatus.RUNNING,
                TaskJobRecord.lease_expires_at < now,
            )
            .with_for_update(skip_locked=True)
        ).scalars()
    )

    if not jobs:
        db.rollback()
        return 0

    abandoned: list[tuple[TaskJobRecord, TaskRecord]] = []
    for job in jobs:
        job.status = JobStatus.FAILED
        job.finished_at = now
        job.lease_expires_at = None
        job.last_error = LEASE_EXPIRED
        task = db.get(TaskRecord, job.task_id)
        if task is not None:
            task.status = TaskStatus.FAILED
            task.updated_at = now
            abandoned.append((job, task))
    db.commit()

    for job, task in abandoned:
        logger.warning(
            "task_abandoned",
            extra={
                "event": "task_abandoned",
                "task_id": str(task.task_id),
                "trace_id": str(task.trace_id),
                "job_id": str(job.job_id),
                "node": job.kind,
                "status": JobStatus.FAILED,
                "error_type": LEASE_EXPIRED,
            },
        )
        record_event(
            db,
            task.task_id,
            task.trace_id,
            "TASK_ABANDONED",
            "worker",
            {
                "job_id": str(job.job_id),
                "kind": job.kind,
                "locked_by": job.locked_by,
                "attempts": job.attempts,
            },
        )

    return len(jobs)
