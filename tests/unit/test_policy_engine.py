from app.policies.engine import PolicyEngine
from app.policies.loader import load_policy_config


def engine() -> PolicyEngine:
    return PolicyEngine(
        load_policy_config("policies/quality-gates.yaml")
    )


def test_requirements_policy_blocks_missing_artifact() -> None:
    decision = engine().evaluate(
        "REQ-001",
        {"requirements": None},
    )

    assert decision.passed is False
    assert decision.action == "BLOCK"


def test_architecture_policy_allows_artifact() -> None:
    decision = engine().evaluate(
        "ARCH-001",
        {"architecture": {"style": "modular"}},
    )

    assert decision.passed is True
    assert decision.action == "ALLOW"
