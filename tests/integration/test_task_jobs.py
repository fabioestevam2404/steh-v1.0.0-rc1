import io
import json
import logging
from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from app.core.logging import build_handler
from app.db.models import AuditEventRecord, TaskJobRecord, TaskRecord
from app.db.session import new_session
from app.models.contracts import TaskCreate, TaskStatus, ids, utc_now
from app.models.human_review import HumanReviewArtifact, HumanReviewDecision, HumanReviewStatus
from app.services import jobs as jobs_service
from app.services import tasks as task_service
from app.services.jobs import (
    LEASE_EXPIRED,
    JobKind,
    JobStatus,
    claim_next_job,
    enqueue_job,
    reap_expired_jobs,
    renew_lease,
)
from app.services.metrics import render_state_metrics
from app.worker import process_job


def _new_task() -> TaskRecord:
    task_id, trace_id = ids()
    with new_session() as db:
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
    with new_session() as db:
        return set(
            db.execute(
                select(AuditEventRecord.event_type).where(AuditEventRecord.task_id == task_id)
            ).scalars()
        )


def _drain_queued() -> None:
    """Keep these tests independent of jobs left over by other tests."""
    with new_session() as db:
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
    with new_session() as db:
        first = enqueue_job(db, db.merge(first_task), JobKind.EXECUTE_TASK)
        second = enqueue_job(db, db.merge(second_task), JobKind.EXECUTE_TASK)
        first_id, second_id = first.job_id, second.job_id

    with new_session() as holder, new_session() as other:
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
    with new_session() as db:
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
    with new_session() as db:
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
    with new_session() as db:
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


@pytest.mark.integration
def test_worker_logs_carry_task_trace_and_job_ids() -> None:
    _drain_queued()
    task = _new_task()
    stream = io.StringIO()
    handler = build_handler(stream)
    loggers = [logging.getLogger(name) for name in ("steh.worker", "steh.jobs")]
    for logger in loggers:
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    try:
        with new_session() as db:
            queued_id = enqueue_job(db, db.merge(task), JobKind.EXECUTE_TASK).job_id
            job = claim_next_job(db, "worker-logs", lease_seconds=60)
            assert job is not None and job.job_id == queued_id
            process_job(db, job, "worker-logs", lease_seconds=60)
    finally:
        for logger in loggers:
            logger.removeHandler(handler)

    lines = [json.loads(line) for line in stream.getvalue().splitlines()]
    by_event = {line["event"]: line for line in lines}

    assert by_event["job_queued"]["job_id"] == str(queued_id)
    failed = by_event["job_failed"]
    assert failed["task_id"] == str(task.task_id)
    assert failed["trace_id"] == str(task.trace_id)
    assert failed["job_id"] == str(queued_id)
    assert failed["error_type"] == "ValueError"
    assert failed["duration_ms"] >= 0


def _job_that_fails_to_insert(real_new_job: Any) -> Any:
    def broken(*args: Any, **kwargs: Any) -> TaskJobRecord:
        job: TaskJobRecord = real_new_job(*args, **kwargs)
        job.kind = "X" * 40  # exceeds VARCHAR(32): PostgreSQL rejects the insert
        return job

    return broken


@pytest.mark.integration
def test_task_is_not_persisted_when_its_job_cannot_be_queued(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = f"Atomicity check {uuid4()} for task and job creation."
    monkeypatch.setattr(task_service, "new_job", _job_that_fails_to_insert(jobs_service.new_job))

    with new_session() as db, pytest.raises(DBAPIError):
        task_service.accept_task(db, TaskCreate(request=request))

    with new_session() as db:
        stored = db.execute(select(TaskRecord).where(TaskRecord.request == request)).first()
    assert stored is None


@pytest.mark.integration
def test_review_claim_is_rolled_back_when_resume_cannot_be_queued(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _new_task()
    now = utc_now()
    with new_session() as db:
        record = db.get(TaskRecord, task.task_id)
        assert record is not None
        record.status = TaskStatus.HUMAN_REVIEW
        record.human_review = HumanReviewArtifact(
            status=HumanReviewStatus.PENDING,
            requested_at=now,
            expires_at=now + timedelta(minutes=30),
            policy_result_count=0,
        ).model_dump(mode="json")
        db.commit()

    monkeypatch.setattr(task_service, "new_job", _job_that_fails_to_insert(jobs_service.new_job))
    decision = HumanReviewDecision(
        decision="APPROVE", justification="Approve to exercise the atomic claim."
    )
    with new_session() as db, pytest.raises(DBAPIError):
        task_service.claim_human_review(db, task.task_id, "reviewer", decision)

    with new_session() as db:
        stored = db.get(TaskRecord, task.task_id)
        assert stored is not None
        assert stored.status == TaskStatus.HUMAN_REVIEW
        jobs = db.execute(select(TaskJobRecord).where(TaskJobRecord.task_id == task.task_id)).all()
    assert jobs == []
    assert "HUMAN_REVIEW_DECIDED" not in _event_types(task.task_id)


def _metric(payload: str, name: str) -> float:
    line = next(line for line in payload.splitlines() if line.startswith(f"{name} "))
    return float(line.rsplit(" ", 1)[1])


@pytest.mark.integration
def test_queue_metrics_reflect_database_state() -> None:
    _drain_queued()
    queued_task, expired_task = _new_task(), _new_task()
    with new_session() as db:
        enqueue_job(db, db.merge(queued_task), JobKind.EXECUTE_TASK)
        enqueue_job(db, db.merge(expired_task), JobKind.REVIEW_PULL_REQUEST)
        # Claim the oldest queued job (the EXECUTE_TASK one) and let its lease expire.
        running = claim_next_job(db, "worker-metrics", lease_seconds=60)
        assert running is not None and running.task_id == queued_task.task_id
        running.lease_expires_at = utc_now() - timedelta(seconds=5)
        queued = db.execute(
            select(TaskJobRecord).where(TaskJobRecord.task_id == expired_task.task_id)
        ).scalar_one()
        queued.created_at = utc_now() - timedelta(minutes=10)
        db.commit()

        payload = render_state_metrics(db)

    assert 'steh_tasks{status="QUEUED"}' in payload
    assert 'steh_task_jobs{kind="REVIEW_PULL_REQUEST",status="QUEUED"}' in payload
    assert 'steh_task_jobs{kind="EXECUTE_TASK",status="RUNNING"}' in payload
    assert _metric(payload, "steh_task_jobs_expired_leases") >= 1
    assert _metric(payload, "steh_task_jobs_oldest_queued_age_seconds") >= 590
    assert "steh_task_job_duration_seconds_count" in payload
