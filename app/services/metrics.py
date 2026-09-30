"""Task and job-queue metrics derived from PostgreSQL at scrape time.

The API and the worker are separate processes, so in-memory counters in the
worker would never reach the API's /metrics. Reading the shared database keeps
the numbers correct for any number of API and worker replicas (ADR-016).
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import TaskJobRecord, TaskRecord
from app.models.contracts import utc_now
from app.services.jobs import JobStatus


def _label(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def render_state_metrics(db: Session) -> str:
    now = utc_now()
    lines = [
        "# HELP steh_tasks Tasks by current status.",
        "# TYPE steh_tasks gauge",
    ]
    for status, count in db.execute(
        select(TaskRecord.status, func.count())
        .group_by(TaskRecord.status)
        .order_by(TaskRecord.status)
    ):
        lines.append(f'steh_tasks{{status="{_label(status)}"}} {count}')

    lines += [
        "# HELP steh_task_jobs Task jobs by kind and status.",
        "# TYPE steh_task_jobs gauge",
    ]
    for kind, status, count in db.execute(
        select(TaskJobRecord.kind, TaskJobRecord.status, func.count())
        .group_by(TaskJobRecord.kind, TaskJobRecord.status)
        .order_by(TaskJobRecord.kind, TaskJobRecord.status)
    ):
        lines.append(f'steh_task_jobs{{kind="{_label(kind)}",status="{_label(status)}"}} {count}')

    oldest_queued = db.execute(
        select(func.min(TaskJobRecord.created_at)).where(TaskJobRecord.status == JobStatus.QUEUED)
    ).scalar_one()
    oldest_age = (now - oldest_queued).total_seconds() if oldest_queued is not None else 0.0
    lines += [
        "# HELP steh_task_jobs_oldest_queued_age_seconds Age of the oldest queued job "
        "(0 when the queue is empty). A growing value means no worker is consuming.",
        "# TYPE steh_task_jobs_oldest_queued_age_seconds gauge",
        f"steh_task_jobs_oldest_queued_age_seconds {oldest_age:.3f}",
    ]

    expired = db.execute(
        select(func.count()).where(
            TaskJobRecord.status == JobStatus.RUNNING,
            TaskJobRecord.lease_expires_at < now,
        )
    ).scalar_one()
    lines += [
        "# HELP steh_task_jobs_expired_leases Running jobs whose lease already expired "
        "(pending TASK_ABANDONED).",
        "# TYPE steh_task_jobs_expired_leases gauge",
        f"steh_task_jobs_expired_leases {expired}",
    ]

    duration = func.extract("epoch", TaskJobRecord.finished_at - TaskJobRecord.started_at)
    lines += [
        "# HELP steh_task_job_duration_seconds Duration of finished jobs.",
        "# TYPE steh_task_job_duration_seconds summary",
    ]
    for kind, status, count, total in db.execute(
        select(TaskJobRecord.kind, TaskJobRecord.status, func.count(), func.sum(duration))
        .where(
            TaskJobRecord.finished_at.is_not(None),
            TaskJobRecord.started_at.is_not(None),
        )
        .group_by(TaskJobRecord.kind, TaskJobRecord.status)
        .order_by(TaskJobRecord.kind, TaskJobRecord.status)
    ):
        labels = f'kind="{_label(kind)}",status="{_label(status)}"'
        lines.append(f"steh_task_job_duration_seconds_sum{{{labels}}} {float(total or 0):.3f}")
        lines.append(f"steh_task_job_duration_seconds_count{{{labels}}} {count}")

    return "\n".join(lines) + "\n"
