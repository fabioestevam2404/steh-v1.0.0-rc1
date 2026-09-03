from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import Principal, get_principal, require_reviewer
from app.db.models import TaskRecord
from app.db.session import get_db
from app.models.contracts import (
    ArchitectureResult,
    RequirementsResult,
    TaskCreate,
    TaskResponse,
    TaskStatus,
    ids,
)
from app.models.human_review import HumanReviewArtifact, HumanReviewDecision
from app.models.specification import SoftwareSpecification
from app.models.test_plan import TestPlan
from app.services.audit import get_task_audit, record_event
from app.services.security import get_security_findings
from app.services.tasks import (
    HumanReviewConflictError,
    execute_task,
    resume_human_review,
)

router = APIRouter(
    prefix="/api/v1/tasks",
    tags=["tasks"],
    dependencies=[Depends(get_principal)],
)

DbSession = Annotated[Session, Depends(get_db)]
ReviewerPrincipal = Annotated[Principal, Depends(require_reviewer)]


def _response(record: TaskRecord) -> TaskResponse:
    return TaskResponse(
        task_id=record.task_id,
        trace_id=record.trace_id,
        status=TaskStatus(record.status),
        requirements=(
            RequirementsResult.model_validate(record.requirements)
            if record.requirements is not None
            else None
        ),
        specification=(
            SoftwareSpecification.model_validate(record.specification)
            if record.specification is not None
            else None
        ),
        architecture=(
            ArchitectureResult.model_validate(record.architecture)
            if record.architecture is not None
            else None
        ),
        security_review=record.security_review,
        risk_level=record.risk_level,
        implementation=record.implementation,
        test_plan=(
            TestPlan.model_validate(record.test_plan)
            if record.test_plan is not None
            else None
        ),
        validation=record.validation,
        rework_count=record.rework_count,
        external_scan=record.external_scan,
        rework_decision=record.rework_decision,
        human_review=(
            HumanReviewArtifact.model_validate(record.human_review)
            if record.human_review is not None
            else None
        ),
        created_at=record.created_at,
    )


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    payload: TaskCreate,
    db: DbSession,
) -> TaskResponse:
    task_id, trace_id = ids()

    record = TaskRecord(
        task_id=task_id,
        trace_id=trace_id,
        request=payload.request,
        status="CREATED",
    )

    db.add(record)
    db.commit()

    record_event(
        db,
        task_id,
        trace_id,
        "TASK_CREATED",
        "api",
        {},
    )

    try:
        completed = execute_task(
            db,
            task_id,
            trace_id,
            payload,
        )
        return _response(completed)

    except Exception as exc:
        record.status = "FAILED"
        db.commit()

        record_event(
            db,
            task_id,
            trace_id,
            "TASK_FAILED",
            "api",
            {},
        )

        raise HTTPException(
            status_code=500,
            detail="Task execution failed.",
        ) from exc


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
)
def get_task(
    task_id: UUID,
    db: DbSession,
) -> TaskResponse:
    record = db.get(TaskRecord, task_id)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found.",
        )

    return _response(record)


@router.post(
    "/{task_id}/human-review",
    response_model=TaskResponse,
)
def decide_human_review(
    task_id: UUID,
    payload: HumanReviewDecision,
    db: DbSession,
    principal: ReviewerPrincipal,
) -> TaskResponse:
    try:
        record = resume_human_review(
            db,
            task_id,
            principal.subject,
            payload,
        )
    except HumanReviewConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return _response(record)


@router.get("/{task_id}/audit")
def audit_task(
    task_id: UUID,
    db: DbSession,
) -> dict[str, Any]:
    record = db.get(TaskRecord, task_id)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found.",
        )

    runs, events = get_task_audit(
        db,
        task_id,
    )

    return {
        "task_id": str(task_id),
        "trace_id": str(record.trace_id),
        "agent_runs": [
            {
                "run_id": str(run.run_id),
                "agent_name": run.agent_name,
                "status": run.status,
                "result": run.result,
                "findings": run.findings,
                "evidence": run.evidence,
                "confidence": run.confidence,
                "started_at": run.started_at,
                "completed_at": run.completed_at,
            }
            for run in runs
        ],
        "events": [
            {
                "event_id": str(event.event_id),
                "event_type": event.event_type,
                "actor": event.actor,
                "payload": event.payload,
                "created_at": event.created_at,
            }
            for event in events
        ],
    }


@router.get("/{task_id}/security")
def security_task(
    task_id: UUID,
    db: DbSession,
) -> dict[str, Any]:
    record = db.get(TaskRecord, task_id)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found.",
        )

    findings = get_security_findings(
        db,
        task_id,
    )

    return {
        "task_id": str(task_id),
        "trace_id": str(record.trace_id),
        "risk_level": record.risk_level,
        "security_review": record.security_review,
        "findings": [
            {
                "finding_id": str(f.finding_id),
                "severity": f.severity,
                "category": f.category,
                "title": f.title,
                "description": f.description,
                "affected_component": f.affected_component,
                "threat": f.threat,
                "recommendation": f.recommendation,
                "evidence": f.evidence,
                "status": f.status,
                "created_at": f.created_at,
            }
            for f in findings
        ],
    }


@router.post("/{task_id}/external-validation")
def external_validation(
    task_id: UUID,
    db: DbSession,
) -> dict[str, Any]:
    from app.orchestration.rework import ReworkController
    from app.services.external_validation import ExternalValidationService

    record = db.get(
        TaskRecord,
        task_id,
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found.",
        )

    if not record.implementation:
        raise HTTPException(
            status_code=409,
            detail="No implementation artifact.",
        )

    try:
        evidence = ExternalValidationService().run(
            str(task_id)
        )

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "External validation unavailable: "
                f"{type(exc).__name__}"
            ),
        ) from exc

    serialized = [
        item.model_dump(mode="json")
        for item in evidence
    ]

    reasons = []

    for item in serialized:
        if not item["success"]:
            reasons.append(
                f'{item["scanner"]}: scanner execution failed'
            )

        for finding in item["findings"]:
            if finding.get("severity") in {
                "HIGH",
                "CRITICAL",
            }:
                reasons.append(
                    f'{item["scanner"]}: '
                    f'{finding.get("rule_id", "finding")}'
                )

    decision = ReworkController().decide(
        record.rework_count + 1,
        reasons,
    )

    record.external_scan = serialized
    record.rework_decision = decision.model_dump(
        mode="json"
    )
    record.rework_count = decision.attempt

    if decision.exhausted:
        record.status = "REWORK_EXHAUSTED"

    elif decision.required:
        record.status = "REWORK_REQUIRED"

    else:
        record.status = "COMPLETED"

    db.commit()

    record_event(
        db,
        task_id,
        record.trace_id,
        "EXTERNAL_VALIDATION_COMPLETED",
        "scanner_suite",
        {
            "decision": record.rework_decision,
            "scanner_count": len(serialized),
        },
    )

    return {
        "task_id": str(task_id),
        "status": record.status,
        "external_scan": serialized,
        "rework_decision": record.rework_decision,
    }
