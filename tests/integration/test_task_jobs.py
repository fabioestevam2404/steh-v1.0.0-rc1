from datetime import timedelta

import pytest
from sqlalchemy import select

from app.db.models import AuditEventRecord, TaskJobRecord, TaskRecord
from app.db.session import SessionLocal
from app.models.contracts import TaskStatus, ids, utc_now
from app.services.jobs import (
    LEASE_EXPIRED,
    JobKind,
    JobStatus,
    claim_next_job,
    enqueue_job,
    reap_expired_jobs,
    renew_lease,
)
from app.worker import process_job


def _new_task() -> TaskRecord:
    task_id, trace_id = ids()
    with SessionLocal() as db:
        record = TaskRecord(
            task_id=task_id,
            trace_id=trace_id,
            request="Integration test task for the job queue.",
            status=TaskStatus.QUEUED,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        db.expunge(record)
        return record


def _event_types(task_id: object) -> set[str]:
    with SessionLocal() as db:
        return set(
            db.execute(
                select(AuditEventRecord.event_type).where(AuditEventRecord.task_id == task_id)
            ).scalars()
        )


def _drain_queued() -> None:
    """Keep these tests independent of jobs left over by other tests."""
    with SessionLocal() as db:
        for job in db.execute(
            select(TaskJobRecord).where(TaskJobRecord.status == JobStatus.QUEUED)
        ).scalars():
            job.status = JobStatus.FAILED
            job.last_error = "IntegrationTestCleanup"
        db.commit()


@pytest.mark.integration
def test_concurrent_workers_skip_locked_jobs() -> None:
    _drain_queued()
    first_task, second_task = _new_task(), _new_task()
    with SessionLocal() as db:
        first = enqueue_job(db, db.merge(first_task), JobKind.EXECUTE_TASK)
        second = enqueue_job(db, db.merge(second_task), JobKind.EXECUTE_TASK)
        first_id, second_id = first.job_id, second.job_id

    with SessionLocal() as holder, SessionLocal() as other:
        locked = holder.execute(
            select(TaskJobRecord).where(TaskJobRecord.job_id == first_id).with_for_update()
        ).scalar_one()
        assert locked.status == JobStatus.QUEUED

        claimed = claim_next_job(other, "worker-b", lease_seconds=60)

        assert claimed is not None
        assert claimed.job_id == second_id
        assert claimed.status == JobStatus.RUNNING
        assert claimed.attempts == 1
        assert claimed.locked_by == "worker-b"
        holder.rollback()


@pytest.mark.integration
def test_expired_lease_abandons_task_without_retry() -> None:
    _drain_queued()
    task = _new_task()
    with SessionLocal() as db:
        job = enqueue_job(db, db.merge(task), JobKind.EXECUTE_TASK)
        claimed = claim_next_job(db, "worker-dead", lease_seconds=60)
        assert claimed is not None and claimed.job_id == job.job_id
        claimed.lease_expires_at = utc_now() - timedelta(seconds=1)
        db.commit()

        assert reap_expired_jobs(db) >= 1

        db.expire_all()
        reaped = db.get(TaskJobRecord, job.job_id)
        assert reaped is not None
        assert reaped.status == JobStatus.FAILED
        assert reaped.last_error == LEASE_EXPIRED
        assert reaped.attempts == 1
        stored_task = db.get(TaskRecord, task.task_id)
        assert stored_task is not None
        assert stored_task.status == TaskStatus.FAILED

    assert "TASK_ABANDONED" in _event_types(task.task_id)


@pytest.mark.integration
def test_failed_job_marks_task_failed_and_records_error_type() -> None:
    _drain_queued()
    task = _new_task()
    with SessionLocal() as db:
        # No context bundle was persisted, so the workflow handler must fail.
        enqueue_job(db, db.merge(task), JobKind.EXECUTE_TASK)
        job = claim_next_job(db, "worker-a", lease_seconds=60)
        assert job is not None

        outcome = process_job(db, job, "worker-a", lease_seconds=60)

        assert outcome == JobStatus.FAILED
        db.expire_all()
        stored_job = db.get(TaskJobRecord, job.job_id)
        assert stored_job is not None
        assert stored_job.status == JobStatus.FAILED
        assert stored_job.last_error == "ValueError"
        assert stored_job.finished_at is not None
        stored_task = db.get(TaskRecord, task.task_id)
        assert stored_task is not None
        assert stored_task.status == TaskStatus.FAILED

    assert {"JOB_QUEUED", "TASK_FAILED"} <= _event_types(task.task_id)


@pytest.mark.integration
def test_lease_renewal_requires_owning_worker() -> None:
    _drain_queued()
    task = _new_task()
    with SessionLocal() as db:
        enqueue_job(db, db.merge(task), JobKind.EXECUTE_TASK)
        job = claim_next_job(db, "worker-owner", lease_seconds=30)
        assert job is not None
        job_id = job.job_id

        assert renew_lease(db, job_id, "worker-owner", lease_seconds=600) is True
        assert renew_lease(db, job_id, "worker-intruder", lease_seconds=600) is False

        db.expire_all()
        renewed = db.get(TaskJobRecord, job_id)
        assert renewed is not None and renewed.lease_expires_at is not None
        assert renewed.lease_expires_at > utc_now() + timedelta(seconds=300)
