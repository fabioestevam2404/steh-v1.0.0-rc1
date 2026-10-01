from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.e2e
def test_full_task_workflow(drain_jobs: Callable[[], int]) -> None:
    with TestClient(app) as client:
        create = client.post(
            "/api/v1/tasks",
            json={"request": ("Crie uma API segura e observável para cadastro de clientes.")},
        )

        assert create.status_code == 202

        accepted = create.json()
        task_id = accepted["task_id"]

        assert accepted["status"] == "QUEUED"
        assert accepted["requirements"] is None
        assert create.headers["location"] == f"/api/v1/tasks/{task_id}"
        assert create.headers["retry-after"] == "2"

        assert drain_jobs() >= 1

        fetched = client.get(create.headers["location"])
        assert fetched.status_code == 200
        payload = fetched.json()

        assert payload["status"] == "HUMAN_REVIEW"
        assert payload["requirements"]
        assert payload["specification"]
        assert payload["architecture"]
        assert payload["security_review"]
        assert payload["risk_level"]

        audit = client.get(f"/api/v1/tasks/{task_id}/audit")

        assert audit.status_code == 200

        audit_payload = audit.json()

        agent_names = {run["agent_name"] for run in audit_payload["agent_runs"]}

        assert "requirements_agent" in agent_names
        requirements_run = next(
            run for run in audit_payload["agent_runs"] if run["agent_name"] == "requirements_agent"
        )
        prompt_evidence = [e for e in requirements_run["evidence"] if e["type"] == "agent_prompt"]
        assert prompt_evidence[0]["prompt_id"] == "requirements"
        assert len(prompt_evidence[0]["prompt_sha256"]) == 64
        assert "specification_agent" in agent_names
        assert "architecture_agent" in agent_names
        assert "security_agent" in agent_names

        event_types = {event["event_type"] for event in audit_payload["events"]}

        assert "AGENT_STARTED" in event_types
        assert "AGENT_SUCCEEDED" in event_types
        assert "POLICY_DECISION" in event_types
        assert "TASK_HUMAN_REVIEW" in event_types
        assert "JOB_QUEUED" in event_types
