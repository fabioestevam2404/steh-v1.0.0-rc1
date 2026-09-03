import logging
import time
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from langgraph.types import Command
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.db.models import TaskRecord
from app.models.contracts import TaskCreate, TaskStatus, utc_now
from app.models.human_review import (
    HumanReviewArtifact,
    HumanReviewDecision,
    HumanReviewResume,
    HumanReviewStatus,
)
from app.orchestration.graph import build_graph
from app.orchestration.lifecycle import AgentLifecycle
from app.services.audit import (
    record_event,
)
from app.services.security import persist_security_findings

logger = logging.getLogger("steh.tasks")


class HumanReviewConflictError(ValueError):
    pass


def resolve_review_outcome(
    pending: HumanReviewArtifact,
    payload: HumanReviewDecision,
    decided_at: datetime,
) -> tuple[HumanReviewStatus, str]:
    if decided_at >= pending.expires_at:
        return (
            HumanReviewStatus.EXPIRED,
            "Human review request expired before a decision.",
        )
    if payload.decision == "APPROVE":
        return HumanReviewStatus.APPROVED, payload.justification
    return HumanReviewStatus.REJECTED, payload.justification


def _apply_workflow_result(
    record: TaskRecord,
    result: dict[str, Any],
) -> None:
    record.requirements = result.get("requirements")
    record.specification = result.get("specification")
    record.architecture = result.get("architecture")
    record.security_review = result.get("security_review")
    record.risk_level = result.get("risk_level")
    record.implementation = result.get("implementation")
    record.test_plan = result.get("test_plan")
    record.validation = result.get("validation")
    record.rework_count = result.get("rework_count", 0)
    record.rework_decision = result.get("rework_decision")
    record.human_review = result.get("human_review")
    record.status = result.get("status", "FAILED")
    record.updated_at = utc_now()


def execute_task(
    db: Session,
    task_id: UUID,
    trace_id: UUID,
    payload: TaskCreate,
) -> TaskRecord:
    record = db.get(TaskRecord, task_id)
    if record is None:
        raise ValueError("Task not found")

    record.status = TaskStatus.ANALYZING
    db.commit()

    record_event(
        db,
        task_id,
        trace_id,
        "TASK_STARTED",
        "orchestrator",
        {"request_length": len(payload.request)},
    )

    started = time.perf_counter()

    logger.info(
        "workflow_started",
        extra={
            "task_id": str(task_id),
            "trace_id": str(trace_id),
            "event": "workflow_started",
            "status": "STARTED",
        },
    )

    try:
        lifecycle = AgentLifecycle(db, task_id, trace_id)
        graph = build_graph(lifecycle=lifecycle)
        result = graph.invoke(
            {
                "task_id": str(task_id),
                "trace_id": str(trace_id),
                "user_request": payload.request,
                "status": "ANALYZING",
                "evidence": [],
            },
            config={
                "configurable": {
                    "thread_id": str(task_id),
                }
            },
        )

        _apply_workflow_result(record, result)

        if record.security_review:
            persist_security_findings(
                db,
                task_id,
                trace_id,
                record.security_review.get("findings", []),
            )

        for decision in result.get("policy_results", []):
            record_event(
                db,
                task_id,
                trace_id,
                "POLICY_DECISION",
                "policy_engine",
                decision,
            )

        if record.human_review:
            record_event(
                db,
                task_id,
                trace_id,
                "HUMAN_REVIEW_REQUESTED",
                "orchestrator",
                record.human_review,
            )

        final_event = {
            "COMPLETED": "TASK_COMPLETED",
            "BLOCKED": "TASK_BLOCKED",
            "HUMAN_REVIEW": "TASK_HUMAN_REVIEW",
            "REWORK_REQUIRED": "TASK_REWORK_REQUIRED",
            "REWORK_EXHAUSTED": "TASK_REWORK_EXHAUSTED",
        }.get(record.status, "TASK_FAILED")

        record_event(
            db,
            task_id,
            trace_id,
            final_event,
            "orchestrator",
            {
                "status": str(record.status),
                "risk_level": record.risk_level,
            },
        )

        for decision in result.get("rework_history", []):
            record_event(
                db,
                task_id,
                trace_id,
                "REWORK_DECISION",
                "rework_controller",
                decision,
            )

        db.commit()
        db.refresh(record)

        logger.info(
            "workflow_completed",
            extra={
                "task_id": str(task_id),
                "trace_id": str(trace_id),
                "event": "workflow_completed",
                "duration_ms": round(
                    (time.perf_counter() - started) * 1000,
                    2,
                ),
                "status": str(record.status),
            },
        )

        return record

    except Exception:
        logger.exception(
            "workflow_failed",
            extra={
                "task_id": str(task_id),
                "trace_id": str(trace_id),
                "event": "workflow_failed",
                "status": "FAILED",
            },
        )
        raise


def resume_human_review(
    db: Session,
    task_id: UUID,
    reviewer: str,
    payload: HumanReviewDecision,
) -> TaskRecord:
    record = db.get(TaskRecord, task_id)
    if record is None or record.human_review is None:
        raise HumanReviewConflictError("Human review is not available.")

    pending = HumanReviewArtifact.model_validate(record.human_review)
    if pending.status != HumanReviewStatus.PENDING:
        raise HumanReviewConflictError("Human review was already decided.")

    decided_at = utc_now()
    outcome, justification = resolve_review_outcome(
        pending,
        payload,
        decided_at,
    )

    claimed = db.execute(
        update(TaskRecord)
        .where(
            TaskRecord.task_id == task_id,
            TaskRecord.status == "HUMAN_REVIEW",
        )
        .values(status="RESUMING", updated_at=decided_at)
    )
    if getattr(claimed, "rowcount", 0) != 1:
        db.rollback()
        raise HumanReviewConflictError("Human review is already being processed.")
    db.commit()

    resume = HumanReviewResume(
        status=outcome,
        reviewer=reviewer,
        justification=justification,
        decided_at=decided_at,
    )
    record_event(
        db,
        task_id,
        record.trace_id,
        "HUMAN_REVIEW_DECIDED",
        reviewer,
        resume.model_dump(mode="json"),
    )

    lifecycle = AgentLifecycle(db, task_id, record.trace_id)
    graph = build_graph(lifecycle=lifecycle)
    try:
        result = cast(
            dict[str, Any],
            cast(Any, graph).invoke(
                Command(resume=resume.model_dump(mode="json")),
                config={"configurable": {"thread_id": str(task_id)}},
            ),
        )
    except Exception:
        record.status = "FAILED"
        record.updated_at = utc_now()
        db.commit()
        record_event(
            db,
            task_id,
            record.trace_id,
            "TASK_RESUME_FAILED",
            "orchestrator",
            {"reviewer": reviewer},
        )
        raise

    _apply_workflow_result(record, result)
    policy_results = result.get("policy_results", [])
    for policy_decision in policy_results[pending.policy_result_count:]:
        record_event(
            db,
            task_id,
            record.trace_id,
            "POLICY_DECISION",
            "policy_engine",
            policy_decision,
        )

    for rework_decision in result.get("rework_history", []):
        record_event(
            db,
            task_id,
            record.trace_id,
            "REWORK_DECISION",
            "rework_controller",
            rework_decision,
        )

    final_event = {
        "COMPLETED": "TASK_COMPLETED",
        "BLOCKED": "TASK_BLOCKED",
        "REWORK_EXHAUSTED": "TASK_REWORK_EXHAUSTED",
    }.get(record.status, "TASK_FAILED")
    record_event(
        db,
        task_id,
        record.trace_id,
        final_event,
        "orchestrator",
        {"status": record.status, "reviewer": reviewer},
    )
    db.commit()
    db.refresh(record)
    return record
