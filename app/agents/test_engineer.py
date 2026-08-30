from datetime import datetime, timezone

from app.models.contracts import AgentResult
from app.models.validation import ValidationResult, ValidationStatus
from app.tools.validator import ControlledValidator


class TestAgent:
    def __init__(self, validator: ControlledValidator | None = None) -> None:
        self.validator = validator or ControlledValidator()

    def run(self, task_id: str, implementation: dict) -> AgentResult:
        tests = self.validator.syntax_tests(task_id)
        findings = [
            *self.validator.secret_scan(task_id),
            *self.validator.sast_scan(task_id),
        ]

        test_passed = all(
            item.status in {ValidationStatus.PASS, ValidationStatus.SKIPPED}
            for item in tests
        )
        scanners_passed = not any(
            item.severity in {"CRITICAL", "HIGH"}
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
            findings=[x.model_dump(mode="json") for x in findings],
            evidence=[{
                "type": "validation_evidence",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test_count": len(tests),
                "scan_finding_count": len(findings),
            }],
            confidence=1.0,
        )
