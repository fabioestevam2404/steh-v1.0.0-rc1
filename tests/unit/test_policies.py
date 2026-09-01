from app.policies.engine import PolicyEngine
from app.policies.loader import PolicyConfig, PolicyRule


def build_policy_engine() -> PolicyEngine:
    config = PolicyConfig(
        version="1.0",
        rules=[
            PolicyRule(
                id="REQ-001",
                description="Requirements must be present",
                check="requirements_present",
                action="BLOCK",
            ),
            PolicyRule(
                id="AUDIT-001",
                description="Evidence must be present",
                check="evidence_present",
                action="BLOCK",
            ),
            PolicyRule(
                id="ARCH-001",
                description="Architecture must be present",
                check="architecture_present",
                action="BLOCK",
            ),
        ],
    )

    return PolicyEngine(config)


def test_policy_blocks_missing():
    engine = build_policy_engine()

    requirements_decision = engine.evaluate(
        "REQ-001",
        {
            "requirements": None,
        },
    )

    architecture_decision = engine.evaluate(
        "ARCH-001",
        {
            "architecture": None,
        },
    )

    assert not requirements_decision.passed
    assert requirements_decision.action == "BLOCK"

    assert not architecture_decision.passed
    assert architecture_decision.action == "BLOCK"


def test_policy_allows_valid():
    engine = build_policy_engine()

    requirements_decision = engine.evaluate(
        "REQ-001",
        {
            "requirements": {
                "x": 1,
            },
        },
    )

    architecture_decision = engine.evaluate(
        "ARCH-001",
        {
            "architecture": {
                "style": "x",
            },
        },
    )

    assert requirements_decision.passed
    assert requirements_decision.action == "ALLOW"

    assert architecture_decision.passed
    assert architecture_decision.action == "ALLOW"


def test_policy_requires_evidence():
    engine = build_policy_engine()

    missing_evidence = engine.evaluate(
        "AUDIT-001",
        {
            "evidence": [],
        },
    )

    valid_evidence = engine.evaluate(
        "AUDIT-001",
        {
            "evidence": [
                {
                    "type": "test_evidence",
                }
            ],
        },
    )

    assert not missing_evidence.passed
    assert missing_evidence.action == "BLOCK"

    assert valid_evidence.passed
    assert valid_evidence.action == "ALLOW"