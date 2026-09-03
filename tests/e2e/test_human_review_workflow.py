import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.e2e
def test_human_approval_resumes_checkpoint_once() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/tasks",
            json={
                "request": (
                    "Crie uma API segura e auditável para cadastro de clientes."
                )
            },
        )
        assert created.status_code == 201
        pending = created.json()
        assert pending["status"] == "HUMAN_REVIEW"
        assert pending["human_review"]["status"] == "PENDING"

        task_id = pending["task_id"]
        approved = client.post(
            f"/api/v1/tasks/{task_id}/human-review",
            json={
                "decision": "APPROVE",
                "justification": "Risk accepted with compensating controls.",
            },
        )
        assert approved.status_code == 200
        completed = approved.json()
        assert completed["status"] == "COMPLETED"
        assert completed["human_review"]["status"] == "APPROVED"
        assert completed["human_review"]["reviewer"] == "local-development"
        assert completed["implementation"]
        assert completed["validation"]

        duplicate = client.post(
            f"/api/v1/tasks/{task_id}/human-review",
            json={
                "decision": "APPROVE",
                "justification": "Duplicate approval must not resume the task.",
            },
        )
        assert duplicate.status_code == 409

        audit = client.get(f"/api/v1/tasks/{task_id}/audit")
        assert audit.status_code == 200
        events = audit.json()["events"]
        assert any(
            event["event_type"] == "HUMAN_REVIEW_DECIDED"
            and event["actor"] == "local-development"
            for event in events
        )
