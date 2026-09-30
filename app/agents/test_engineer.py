from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Any

from app.models.contracts import AgentResult
from app.models.validation import TestEvidence, ValidationResult, ValidationStatus
from app.tools.validator import ControlledValidator

MAX_LISTED_MISSING_FILES = 10


def workspace_integrity(declared: set[str], present: set[str]) -> TestEvidence:
    """Fail closed unless every file the implementation declared is in the workspace.

    Without this check an empty workspace validated as PASS: syntax tests were
    SKIPPED and scanners found nothing because there was nothing to scan.
    """
    if not declared:
        return TestEvidence(
            name="workspace_integrity",
            status=ValidationStatus.FAIL,
            details="Implementation declared no files; nothing was validated.",
        )
    missing = sorted(declared - present)
    if missing:
        listed = ", ".join(missing[:MAX_LISTED_MISSING_FILES])
        more = len(missing) - MAX_LISTED_MISSING_FILES
        suffix = f" (+{more} more)" if more > 0 else ""
        return TestEvidence(
            name="workspace_integrity",
            status=ValidationStatus.FAIL,
            details=f"Declared files missing from the workspace: {listed}{suffix}.",
        )
    return TestEvidence(
        name="workspace_integrity",
        status=ValidationStatus.PASS,
        details=f"All {len(declared)} declared files are present in the workspace.",
    )


def _declared_files(implementation: dict[str, Any]) -> set[str]:
    paths = [
        *implementation.get("files_created", []),
        *implementation.get("files_modified", []),
    ]
    return {PurePosixPath(path).as_posix() for path in paths}


class TestAgent:
    __test__ = False

    def __init__(
        self,
        validator: ControlledValidator | None = None,
    ) -> None:
        self.validator = validator or ControlledValidator()

    def run(
        self,
        task_id: str,
        implementation: dict[str, Any],
    ) -> AgentResult:
        tests = [
            workspace_integrity(
                _declared_files(implementation),
                self.validator.relative_files(task_id),
            ),
            *self.validator.syntax_tests(task_id),
        ]
        findings = [
            *self.validator.secret_scan(task_id),
            *self.validator.sast_scan(task_id),
        ]

        test_passed = all(
            item.status
            in {
                ValidationStatus.PASS,
                ValidationStatus.SKIPPED,
            }
            for item in tests
        )

        scanners_passed = not any(
            item.severity
            in {
                "CRITICAL",
                "HIGH",
            }
            for item in findings
        )

        result = ValidationResult(
            tests=tests,
            scan_findings=findings,
            test_passed=test_passed,
            scanners_passed=scanners_passed,
            summary=(
                "Validation passed."
                if test_passed and scanners_passed
                else "Validation requires rework."
            ),
        )

        return AgentResult(
            agent="test_agent",
            status="SUCCESS",
            result=result.model_dump(mode="json"),
            findings=[item.model_dump(mode="json") for item in findings],
            evidence=[
                {
                    "type": "validation_evidence",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "test_count": len(tests),
                    "scan_finding_count": len(findings),
                }
            ],
            confidence=1.0,
        )
