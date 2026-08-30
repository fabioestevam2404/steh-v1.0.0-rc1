from app.agents.security import SecurityAgent


def test_security_agent_stub_returns_threat_model_and_findings() -> None:
    agent = SecurityAgent("stub", "test", None)

    result = agent.run(
        {"functional_requirements": ["manage customers"]},
        {
            "components": [
                {
                    "name": "API Layer",
                    "responsibility": "HTTP interface",
                    "technology_options": ["FastAPI"],
                }
            ]
        },
    )

    review = result.result

    assert result.status == "SUCCESS"
    assert review["threat_model"]["assets"]
    assert review["threat_model"]["threats"]
    assert review["findings"]
    assert review["overall_risk"] in {
        "INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"
    }
