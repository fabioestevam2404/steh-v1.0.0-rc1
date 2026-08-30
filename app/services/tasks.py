import logging
import time
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import TaskRecord
from app.models.contracts import TaskCreate, TaskStatus, utc_now
from app.orchestration.graph import build_graph
from app.orchestration.lifecycle import AgentLifecycle
from app.services.audit import (
    complete_agent_run,
    fail_agent_run,
    record_event,
    start_agent_run,
)
from app.services.security import persist_security_findings

logger = logging.getLogger("steh.tasks")


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

        record.requirements = result.get("requirements")
        record.architecture = result.get("architecture")
        record.security_review = result.get("security_review")
        record.risk_level = result.get("risk_level")
        record.implementation = result.get("implementation")
        record.validation = result.get("validation")
        record.rework_count = result.get("rework_count", 0)
        record.status = result.get("status", "FAILED")
        record.updated_at = utc_now()

        if result.get("implementation_run"):
            runs["implementation_agent"] = start_agent_run(
                db, task_id, trace_id, "implementation_agent"
            )
            ir = result["implementation_run"]
            complete_agent_run(
                db,
                runs["implementation_agent"],
                ir["result"],
                ir.get("evidence", []),
                ir.get("confidence", 0.0),
            )

        if result.get("test_run"):
            runs["test_agent"] = start_agent_run(
                db, task_id, trace_id, "test_agent"
            )
            tr = result["test_run"]
            complete_agent_run(
                db,
                runs["test_agent"],
                tr["result"],
                tr.get("evidence", []),
                tr.get("confidence", 0.0),
            )

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

        final_event = {
            "COMPLETED": "TASK_COMPLETED",
            "BLOCKED": "TASK_BLOCKED",
            "HUMAN_REVIEW": "TASK_HUMAN_REVIEW",
            "REWORK_REQUIRED": "TASK_REWORK_REQUIRED",
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

    except Exception as exc:
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
