from app.policies.loader import load_policy_config


def test_policy_file_loads() -> None:
    config = load_policy_config("policies/quality-gates.yaml")

    assert config.version == "0.2.1"
    assert {rule.id for rule in config.rules} == {
        "AUDIT-001",
        "REQ-001",
        "ARCH-001",
    }
