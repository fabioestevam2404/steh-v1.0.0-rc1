from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import SecurityFindingRecord


def persist_security_findings(
    db: Session,
    task_id: UUID,
    trace_id: UUID,
    findings: list[dict],
) -> None:
    for finding in findings:
        db.add(
            SecurityFindingRecord(
                finding_id=UUID(str(finding["finding_id"])),
                task_id=task_id,
                trace_id=trace_id,
                title=finding["title"],
                description=finding["description"],
                severity=finding["severity"],
                category=finding["category"],
                affected_component=finding["affected_component"],
                threat=finding["threat"],
                recommendation=finding["recommendation"],
                evidence=finding.get("evidence", []),
                status=finding.get("status", "OPEN"),
            )
        )
    db.commit()


def get_security_findings(
    db: Session,
    task_id: UUID,
) -> list[SecurityFindingRecord]:
    return list(
        db.scalars(
            select(SecurityFindingRecord)
            .where(SecurityFindingRecord.task_id == task_id)
            .order_by(SecurityFindingRecord.created_at)
        )
    )
