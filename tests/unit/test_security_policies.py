from app.policies.engine import PolicyEngine
from app.policies.loader import load_policy_config


def engine() -> PolicyEngine:
    return PolicyEngine(
        load_policy_config("policies/quality-gates.yaml")
    )


def test_critical_finding_blocks() -> None:
    context = {
        "security_review": {
            "threat_model": {
                "security_requirements": ["auth required"]
            },
            "findings": [
                {
                    "severity": "CRITICAL",
                    "status": "OPEN",
                }
            ],
        }
    }

    decision = engine().evaluate("SEC-001", context)

    assert decision.passed is False
    assert decision.action == "BLOCK"


def test_high_finding_requires_human_review() -> None:
    context = {
        "security_review": {
            "threat_model": {
                "security_requirements": ["auth required"]
            },
            "findings": [
                {
                    "severity": "HIGH",
                    "status": "OPEN",
                }
            ],
        }
    }

    decision = engine().evaluate("SEC-002", context)

    assert decision.passed is False
    assert decision.action == "HUMAN_REVIEW"


def test_threat_model_and_security_requirements_are_required() -> None:
    no_model = engine().evaluate(
        "SEC-003",
        {"security_review": {}},
    )
    no_requirements = engine().evaluate(
        "SEC-004",
        {
            "security_review": {
                "threat_model": {
                    "security_requirements": []
                }
            }
        },
    )

    assert no_model.action == "BLOCK"
    assert no_requirements.action == "BLOCK"
