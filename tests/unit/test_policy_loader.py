from app.policies.loader import load_policy_config


def test_policy_file_loads() -> None:
    config = load_policy_config("policies/quality-gates.yaml")

    assert config.version == "0.4"

    assert {rule.id for rule in config.rules} == {
        "AUDIT-001",
        "REQ-001",
        "ARCH-001",
        "SPEC-001",
        "SPEC-002",
        "SPEC-003",
        "TRACE-001",
        "SEC-001",
        "SEC-002",
        "SEC-003",
        "SEC-004",
        "IMPL-001",
        "TESTPLAN-001",
        "TESTPLAN-002",
        "TESTPLAN-003",
        "TEST-001",
        "SCAN-001",
    }
