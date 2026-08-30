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

        assert payload["status"] == "COMPLETED"
        assert payload["requirements"]
        assert payload["architecture"]

        task_id = payload["task_id"]

        audit = client.get(
            f"/api/v1/tasks/{task_id}/audit"
        )

        assert audit.status_code == 200

        audit_payload = audit.json()

        assert len(audit_payload["agent_runs"]) == 2

        event_types = {
            event["event_type"]
            for event in audit_payload["events"]
        }

        assert "AGENT_STARTED" in event_types
        assert "AGENT_SUCCEEDED" in event_types
        assert "POLICY_DECISION" in event_types
        assert "TASK_COMPLETED" in event_types
