from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.policies.loader import PolicyConfig, PolicyRule


@dataclass(frozen=True)
class PolicyDecision:
    policy_id: str
    passed: bool
    action: str
    reason: str


def _severity_count(
    context: Mapping[str, Any],
    severity: str,
) -> int:
    review = context.get("security_review") or {}
    findings = review.get("findings") or []

    return sum(
        1
        for finding in findings
        if finding.get("severity") == severity
        and finding.get("status", "OPEN") == "OPEN"
    )


def _check(
    rule: PolicyRule,
    context: Mapping[str, Any],
) -> bool:
    security_review = context.get("security_review") or {}
    threat_model = security_review.get("threat_model") or {}

    checks = {
        "requirements_present": bool(
            context.get("requirements")
        ),
        "evidence_present": bool(
            context.get("evidence")
        ),
        "architecture_present": bool(
            context.get("architecture")
        ),
        "no_critical_security_findings": (
            _severity_count(
                context,
                "CRITICAL",
            )
            == 0
        ),
        "no_high_security_findings": (
            _severity_count(
                context,
                "HIGH",
            )
            == 0
        ),
        "threat_model_present": bool(
            threat_model
        ),
        "security_requirements_present": bool(
            threat_model.get(
                "security_requirements"
            )
        ),
        "implementation_present": bool(
            context.get("implementation")
        ),
        "tests_passed": bool(
            (
                context.get("validation")
                or {}
            ).get("test_passed")
        ),
        "scanners_passed": bool(
            (
                context.get("validation")
                or {}
            ).get("scanners_passed")
        ),
    }

    if rule.check not in checks:
        raise ValueError(
            f"Unsupported policy check: {rule.check}"
        )

    return checks[rule.check]


class PolicyEngine:
    def __init__(
        self,
        config: PolicyConfig,
    ) -> None:
        self.config = config

    def evaluate(
        self,
        policy_id: str,
        context: Mapping[str, Any],
    ) -> PolicyDecision:
        rule = next(
            (
                item
                for item in self.config.rules
                if item.id == policy_id
            ),
            None,
        )

        if rule is None:
            raise KeyError(
                f"Policy not found: {policy_id}"
            )

        passed = _check(
            rule,
            context,
        )

        return PolicyDecision(
            policy_id=rule.id,
            passed=passed,
            action=(
                "ALLOW"
                if passed
                else rule.action
            ),
            reason=(
                f"{rule.description}: passed"
                if passed
                else f"{rule.description}: failed"
            ),
        )
