from datetime import UTC, datetime
from typing import Any

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.models.contracts import AgentResult
from app.models.security import (
    SecurityFinding,
    SecurityReviewResult,
    Severity,
    Threat,
    ThreatModel,
)


class SecurityAgent:
    def __init__(
        self,
        mode: str,
        model: str,
        api_key: str | None,
    ) -> None:
        self.mode = mode
        self.model = model
        self.api_key = api_key

    def run(
    self,
    requirements: dict[str, Any],
    architecture: dict[str, Any],
) -> AgentResult:
        if self.mode == "openai":
            return self._run_openai(
                requirements,
                architecture,
            )

        return self._run_stub(
            requirements,
            architecture,
        )

    def _run_openai(
        self,
        requirements: dict[str, Any],
        architecture: dict[str, Any],
    ) -> AgentResult:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY required")

        llm = ChatOpenAI(
            model=self.model,
            temperature=0,
            api_key=SecretStr(self.api_key),
        ).with_structured_output(
            SecurityReviewResult
        )

        prompt = f"""
You are the Security Agent of the Software Trust Engineering Harness.

Perform an adversarial security review of the approved requirements and
architecture. Use STRIDE as a threat-modeling lens, but do not claim that
STRIDE proves the system secure.

Identify:
- assets
- trust boundaries
- entry points
- threats
- controls
- residual risks
- security requirements
- concrete security findings with severity

Severity must be one of INFO, LOW, MEDIUM, HIGH, CRITICAL.

Never claim the software is completely secure.
Return only the structured SecurityReviewResult.

REQUIREMENTS:
{requirements}

ARCHITECTURE:
{architecture}
"""

        result = llm.invoke(prompt)

        validated = SecurityReviewResult.model_validate(
            result
        )

        return AgentResult(
            agent="security_agent",
            status="SUCCESS",
            result=validated.model_dump(
                mode="json"
            ),
            findings=[
                finding.model_dump(
                    mode="json"
                )
                for finding in validated.findings
            ],
            evidence=[
                {
                    "type": "security_review",
                    "timestamp": datetime.now(
                        UTC
                    ).isoformat(),
                    "method": (
                        "llm_structured_output"
                    ),
                }
            ],
            confidence=0.88,
        )

    def _run_stub(
    self,
    requirements: dict[str, Any],
    architecture: dict[str, Any],
) -> AgentResult:
        component_names = [
            component.get(
                "name",
                "unknown",
            )
            for component in architecture.get(
                "components",
                [],
            )
            if isinstance(
                component,
                dict,
            )
        ]

        primary_component = (
            component_names[0]
            if component_names
            else "application"
        )

        threat_model = ThreatModel(
            assets=[
                "application data",
                "user identities",
                "audit evidence",
                "configuration and secrets",
            ],
            trust_boundaries=[
                "client to API",
                "API to persistence",
                (
                    "application to external "
                    "LLM provider"
                ),
            ],
            entry_points=[
                "HTTP API",
                "LLM prompt input",
                "database connection",
            ],
            threats=[
                Threat(
                    category="Spoofing",
                    description=(
                        "Unauthorized actor may "
                        "impersonate a legitimate user."
                    ),
                    affected_asset=(
                        "user identities"
                    ),
                    attack_surface="HTTP API",
                    mitigation=(
                        "Require authenticated identities "
                        "and strong authorization."
                    ),
                ),
                Threat(
                    category="Tampering",
                    description=(
                        "Task or audit data may be "
                        "modified without authorization."
                    ),
                    affected_asset="audit evidence",
                    attack_surface=(
                        "persistence layer"
                    ),
                    mitigation=(
                        "Restrict write permissions "
                        "and preserve append-only "
                        "audit semantics."
                    ),
                ),
                Threat(
                    category=(
                        "Information Disclosure"
                    ),
                    description=(
                        "Sensitive information may "
                        "leak through prompts or logs."
                    ),
                    affected_asset=(
                        "application data"
                    ),
                    attack_surface=(
                        "LLM and structured logs"
                    ),
                    mitigation=(
                        "Redact secrets and minimize "
                        "sensitive data sent to "
                        "external providers."
                    ),
                ),
            ],
            controls=[
                "input validation",
                (
                    "least privilege database "
                    "credentials"
                ),
                "structured audit events",
                "secret redaction",
            ],
            residual_risks=[
                (
                    "authentication and authorization "
                    "are not implemented in this alpha"
                ),
                (
                    "external LLM data handling depends "
                    "on provider configuration"
                ),
            ],
            security_requirements=[
                (
                    "authenticate API consumers "
                    "before production exposure"
                ),
                (
                    "authorize access to task "
                    "and audit resources"
                ),
                (
                    "never persist secrets "
                    "in logs or prompts"
                ),
                (
                    "enforce least privilege for "
                    "application database access"
                ),
                (
                    "preserve traceable evidence "
                    "for security decisions"
                ),
            ],
        )

        findings = [
            SecurityFinding(
                title=(
                    "API authentication "
                    "not implemented"
                ),
                description=(
                    "The current alpha exposes task "
                    "endpoints without an application "
                    "authentication layer."
                ),
                severity=Severity.HIGH,
                category="Authentication",
                affected_component=(
                    primary_component
                ),
                threat="Spoofing",
                recommendation=(
                    "Introduce authenticated principals "
                    "and authorization before non-local "
                    "or production exposure."
                ),
                evidence=[
                    (
                        "Alpha 0.3 intentionally has no "
                        "API authentication layer."
                    )
                ],
            ),
            SecurityFinding(
                title=(
                    "Audit immutability is not "
                    "database-enforced"
                ),
                description=(
                    "Audit events are recorded, but "
                    "append-only semantics are not "
                    "enforced by dedicated database "
                    "privileges."
                ),
                severity=Severity.MEDIUM,
                category="Audit Integrity",
                affected_component="PostgreSQL",
                threat="Tampering",
                recommendation=(
                    "Use restricted roles or "
                    "append-only storage controls for "
                    "audit events in a later hardening "
                    "release."
                ),
                evidence=[
                    (
                        "AuditEventRecord remains "
                        "writable by the application role."
                    )
                ],
            ),
        ]

        review = SecurityReviewResult(
            threat_model=threat_model,
            findings=findings,
            overall_risk=Severity.HIGH,
            summary=(
                "The architecture has basic engineering "
                "controls, but the absence of API "
                "authentication is a high-severity "
                "blocker for production exposure."
            ),
        )

        return AgentResult(
            agent="security_agent",
            status="SUCCESS",
            result=review.model_dump(
                mode="json"
            ),
            findings=[
                finding.model_dump(
                    mode="json"
                )
                for finding in findings
            ],
            evidence=[
                {
                    "type": "security_review",
                    "timestamp": datetime.now(
                        UTC
                    ).isoformat(),
                    "method": (
                        "deterministic_stub"
                    ),
                }
            ],
            confidence=0.65,
        )