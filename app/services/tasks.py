import logging
import time
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from langgraph.types import Command
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import TaskRecord
from app.models.context import ContextBundle, ContextSourceInput
from app.models.contracts import TaskCreate, TaskStatus, ids, utc_now
from app.models.human_review import (
    HumanReviewArtifact,
    HumanReviewDecision,
    HumanReviewResume,
    HumanReviewStatus,
)
from app.models.judge import JudgeEvaluationArtifact
from app.orchestration.graph import build_graph
from app.orchestration.lifecycle import AgentLifecycle
from app.services.audit import (
    record_event,
)
from app.services.context import ContextEngine, context_receipt
from app.services.jobs import JobKind, new_job, record_job_queued
from app.services.judge import judge_evaluation_receipt
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
    record.context_bundle = result.get("context_bundle")
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
    record.judge_evaluation = result.get("judge_evaluation")
    record.status = result.get("status", "FAILED")
    record.updated_at = utc_now()


def build_context_bundle(
    request: str,
    sources: list[ContextSourceInput],
) -> ContextBundle:
    settings = get_settings()
    return ContextEngine(
        max_sources=settings.context_max_sources,
        max_tokens=settings.context_max_tokens,
        max_source_tokens=settings.context_max_source_tokens,
    ).build(request, sources)


def persist_context_bundle(
    db: Session,
    record: TaskRecord,
    context_bundle: ContextBundle,
) -> None:
    record.context_bundle = context_bundle.model_dump(mode="json")
    record.updated_at = utc_now()
    db.commit()
    _record_context_event(db, record, context_bundle)


def _record_context_event(
    db: Session,
    record: TaskRecord,
    context_bundle: ContextBundle,
) -> None:
    record_event(
        db,
        record.task_id,
        record.trace_id,
        "CONTEXT_BUNDLE_CREATED",
        "context_engine",
        context_receipt(context_bundle).model_dump(mode="json"),
    )


def accept_task(db: Session, payload: TaskCreate) -> TaskRecord:
    """Validate and persist a task, then queue its workflow (ADR-016).

    Raises ValueError when the context sources are invalid; no task is created.
    """
    context_bundle = build_context_bundle(payload.request, payload.context_sources)

    task_id, trace_id = ids()
    record = TaskRecord(
        task_id=task_id,
        trace_id=trace_id,
        request=payload.request,
        status=TaskStatus.QUEUED,
        context_bundle=context_bundle.model_dump(mode="json"),
    )
    job = new_job(record, JobKind.EXECUTE_TASK)
    # Flush the task first: without a relationship, SQLAlchemy does not order
    # the inserts by the foreign key. Both rows still commit atomically.
    db.add(record)
    db.flush()
    db.add(job)
    db.commit()

    record_event(db, task_id, trace_id, "TASK_CREATED", "api", {})
    _record_context_event(db, record, context_bundle)
    record_job_queued(db, record, job)
    db.refresh(record)
    return record


def invoke_workflow(
    graph: Any,
    config: dict[str, Any],
    start: Any,
    *,
    recover: bool,
    resume_interrupt: bool = False,
) -> dict[str, Any]:
    """Run a workflow thread, or recover it from its last checkpoint (ADR-017).

    Without recovery the graph runs from `start`. With recovery the stored checkpoint
    decides: no checkpoint starts from `start`; pending nodes continue with
    `invoke(None)` so only the interrupted node runs again; a finished thread reuses
    its state. A pending human-review interrupt reuses the state too, unless `start`
    is the resume command that never got applied (`resume_interrupt`).
    Checkpoints are written synchronously so recovery resumes after the last
    completed node.
    """
    if recover:
        snapshot = graph.get_state(config)
        if snapshot.values:
            if snapshot.interrupts:
                if not resume_interrupt:
                    return dict(snapshot.values)
            elif snapshot.next:
                return cast(dict[str, Any], graph.invoke(None, config, durability="sync"))
            else:
                return dict(snapshot.values)
    return cast(dict[str, Any], graph.invoke(start, config, durability="sync"))


def _thread_config(task_id: UUID) -> dict[str, Any]:
    return {"configurable": {"thread_id": str(task_id)}}


def run_task_workflow(db: Session, task_id: UUID, attempt: int = 1) -> TaskRecord:
    """Run the engineering workflow for a task whose context is already persisted.

    From the second attempt on, the workflow is recovered from its checkpoint.
    """
    record = db.get(TaskRecord, task_id)
    if record is None:
        raise ValueError("Task not found")
    if record.context_bundle is None:
        raise ValueError("Task has no context bundle")

    trace_id = record.trace_id
    context_bundle = ContextBundle.model_validate(record.context_bundle)

    record.status = TaskStatus.ANALYZING
    db.commit()

    recover = attempt > 1
    record_event(
        db,
        task_id,
        trace_id,
        "TASK_RECOVERED" if recover else "TASK_STARTED",
        "orchestrator",
        {"attempt": attempt} if recover else {"request_length": len(record.request)},
    )

    started = time.perf_counter()

    logger.info(
        "workflow_started",
        extra={
            "event": "workflow_started",
            "status": "STARTED",
        },
    )

    try:
        lifecycle = AgentLifecycle(db, task_id, trace_id)
        graph = build_graph(lifecycle=lifecycle)
        result = invoke_workflow(
            graph,
            _thread_config(task_id),
            {
                "task_id": str(task_id),
                "trace_id": str(trace_id),
                "user_request": record.request,
                "status": "ANALYZING",
                "context_bundle": context_bundle.model_dump(mode="json"),
                "evidence": [],
            },
            recover=recover,
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

        if record.judge_evaluation:
            evaluation = JudgeEvaluationArtifact.model_validate(record.judge_evaluation)
            record_event(
                db,
                task_id,
                trace_id,
                "JUDGE_EVALUATION",
                "llm_judge_agent",
                judge_evaluation_receipt(evaluation),
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
                "event": "workflow_failed",
                "status": "FAILED",
            },
        )
        raise


def claim_human_review(
    db: Session,
    task_id: UUID,
    reviewer: str,
    payload: HumanReviewDecision,
) -> TaskRecord:
    """Atomically claim a pending review, record the decision and queue the resume."""
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

    resume = HumanReviewResume(
        status=outcome,
        reviewer=reviewer,
        justification=justification,
        decided_at=decided_at,
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

    # The claim and its resume job commit together, so a claimed review is never
    # left in RESUMING without a job to finish it.
    job = new_job(record, JobKind.RESUME_HUMAN_REVIEW, resume.model_dump(mode="json"))
    db.add(job)
    db.commit()

    record_event(
        db,
        task_id,
        record.trace_id,
        "HUMAN_REVIEW_DECIDED",
        reviewer,
        resume.model_dump(mode="json"),
    )
    record_job_queued(db, record, job)
    db.refresh(record)
    return record


def run_human_review_resume(
    db: Session,
    task_id: UUID,
    resume_payload: dict[str, Any],
    attempt: int = 1,
) -> TaskRecord:
    """Resume the interrupted checkpoint with a previously claimed decision."""
    record = db.get(TaskRecord, task_id)
    if record is None or record.human_review is None:
        raise ValueError("Human review is not available.")

    pending = HumanReviewArtifact.model_validate(record.human_review)
    resume = HumanReviewResume.model_validate(resume_payload)
    reviewer = resume.reviewer

    lifecycle = AgentLifecycle(db, task_id, record.trace_id)
    graph = build_graph(lifecycle=lifecycle)
    recover = attempt > 1
    if recover:
        record_event(
            db,
            task_id,
            record.trace_id,
            "TASK_RECOVERED",
            "orchestrator",
            {"attempt": attempt, "reviewer": reviewer},
        )
    try:
        result = invoke_workflow(
            graph,
            _thread_config(task_id),
            Command(resume=resume.model_dump(mode="json")),
            recover=recover,
            resume_interrupt=True,
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
    for policy_decision in policy_results[pending.policy_result_count :]:
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

    if record.judge_evaluation:
        evaluation = JudgeEvaluationArtifact.model_validate(record.judge_evaluation)
        record_event(
            db,
            task_id,
            record.trace_id,
            "JUDGE_EVALUATION",
            "llm_judge_agent",
            judge_evaluation_receipt(evaluation),
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
