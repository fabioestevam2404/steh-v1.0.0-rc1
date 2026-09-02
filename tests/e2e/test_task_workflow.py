import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.e2e
def test_full_task_workflow() -> None:
    with TestClient(app) as client:
        create = client.post(
            "/api/v1/tasks",
            json={
                "request": (
                    "Crie uma API segura e observável "
                    "para cadastro de clientes."
                )
            },
        )

        assert create.status_code == 201

        payload = create.json()

        assert payload["status"] == "HUMAN_REVIEW"
        assert payload["requirements"]
        assert payload["architecture"]
        assert payload["security_review"]
        assert payload["risk_level"]

        task_id = payload["task_id"]

        audit = client.get(
            f"/api/v1/tasks/{task_id}/audit"
        )

        assert audit.status_code == 200

        audit_payload = audit.json()

        agent_names = {
            run["agent_name"]
            for run in audit_payload["agent_runs"]
        }

        assert "requirements_agent" in agent_names
        assert "architecture_agent" in agent_names
        assert "security_agent" in agent_names

        event_types = {
            event["event_type"]
            for event in audit_payload["events"]
        }

        assert "AGENT_STARTED" in event_types
        assert "AGENT_SUCCEEDED" in event_types
        assert "POLICY_DECISION" in event_types
        assert "TASK_HUMAN_REVIEW" in event_types