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


def test_specification_and_test_plan_are_traceable() -> None:
    context = {
        "specification": {
            "requirements": [{"id": "FR-001"}, {"id": "NFR-001"}],
            "acceptance_scenarios": [{
                "id": "AC-001",
                "requirement_ids": ["FR-001", "NFR-001"],
                "given": "a client",
                "when": "it submits a request",
                "then": "the contract is enforced",
            }],
        },
        "test_plan": {"test_cases": [{
            "requirement_ids": ["FR-001", "NFR-001"],
            "test_type": "SECURITY",
            "negative": True,
        }]},
    }

    for policy_id in (
        "SPEC-001", "SPEC-002", "SPEC-003", "TRACE-001",
        "TESTPLAN-001", "TESTPLAN-002", "TESTPLAN-003",
    ):
        assert engine().evaluate(policy_id, context).passed


def test_traceability_gate_blocks_uncovered_requirement() -> None:
    context = {
        "specification": {
            "requirements": [{"id": "FR-001"}, {"id": "FR-002"}],
            "acceptance_scenarios": [{
                "id": "AC-001",
                "requirement_ids": ["FR-001"],
                "given": "valid input",
                "when": "processed",
                "then": "it succeeds",
            }],
        }
    }

    decision = engine().evaluate("TRACE-001", context)

    assert not decision.passed
    assert decision.action == "BLOCK"
