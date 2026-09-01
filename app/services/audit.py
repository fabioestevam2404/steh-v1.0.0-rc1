from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AgentRunRecord, AuditEventRecord


def record_event(
    db: Session,
    task_id: UUID,
    trace_id: UUID,
    event_type: str,
    actor: str,
    payload: dict[str, Any],
) -> AuditEventRecord:
    event = AuditEventRecord(
        task_id=task_id,
        trace_id=trace_id,
        event_type=event_type,
        actor=actor,
        payload=payload,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def start_agent_run(
    db: Session,
    task_id: UUID,
    trace_id: UUID,
    agent_name: str,
) -> AgentRunRecord:
    run = AgentRunRecord(
        run_id=uuid4(),
        task_id=task_id,
        trace_id=trace_id,
        agent_name=agent_name,
        status="STARTED",
        result=None,
        findings=[],
        evidence=[],
        confidence=0.0,
        started_at=datetime.now(UTC),
        completed_at=None,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    record_event(
        db,
        task_id,
        trace_id,
        "AGENT_STARTED",
        agent_name,
        {"run_id": str(run.run_id)},
    )

    return run


def complete_agent_run(
    db: Session,
    run: AgentRunRecord,
    result: dict[str, Any],
    evidence: list[dict[str, Any]],
    confidence: float,
) -> None:
    run.status = "SUCCEEDED"
    run.result = result
    run.evidence = evidence
    run.confidence = confidence
    run.completed_at = datetime.now(UTC)

    db.commit()

    record_event(
        db,
        run.task_id,
        run.trace_id,
        "AGENT_SUCCEEDED",
        run.agent_name,
        {"run_id": str(run.run_id)},
    )


def fail_agent_run(
    db: Session,
    run: AgentRunRecord,
    error_type: str,
) -> None:
    run.status = "FAILED"
    run.completed_at = datetime.now(UTC)

    db.commit()

    record_event(
        db,
        run.task_id,
        run.trace_id,
        "AGENT_FAILED",
        run.agent_name,
        {
            "run_id": str(run.run_id),
            "error_type": error_type,
        },
    )


def get_task_audit(
    db: Session,
    task_id: UUID,
) -> tuple[list[AgentRunRecord], list[AuditEventRecord]]:
    runs = list(
        db.scalars(
            select(AgentRunRecord)
            .where(AgentRunRecord.task_id == task_id)
            .order_by(AgentRunRecord.started_at)
        )
    )

    events = list(
        db.scalars(
            select(AuditEventRecord)
            .where(AuditEventRecord.task_id == task_id)
            .order_by(AuditEventRecord.created_at)
        )
    )

    return runs, events