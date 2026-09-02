import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.e2e
def test_security_layer_end_to_end() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/tasks",
            json={
                "request": (
                    "Crie uma API segura e auditável "
                    "para cadastro de clientes."
                )
            },
        )

        assert created.status_code == 201

        payload = created.json()
        assert payload["requirements"]
        assert payload["specification"]
        assert payload["architecture"]
        assert payload["security_review"]
        assert payload["risk_level"] == "HIGH"
        assert payload["status"] == "HUMAN_REVIEW"

        task_id = payload["task_id"]

        security = client.get(
            f"/api/v1/tasks/{task_id}/security"
        )

        assert security.status_code == 200
        security_payload = security.json()

        assert security_payload["findings"]
        assert any(
            finding["severity"] == "HIGH"
            for finding in security_payload["findings"]
        )

        audit = client.get(
            f"/api/v1/tasks/{task_id}/audit"
        )

        assert audit.status_code == 200
        audit_payload = audit.json()

        agent_names = {
            run["agent_name"]
            for run in audit_payload["agent_runs"]
        }

        assert agent_names == {
            "requirements_agent",
            "specification_agent",
            "architecture_agent",
            "security_agent",
        }

        event_types = {
            event["event_type"]
            for event in audit_payload["events"]
        }

        assert "TASK_HUMAN_REVIEW" in event_types
        assert "POLICY_DECISION" in event_types