from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.e2e
def test_human_approval_resumes_checkpoint_once(drain_jobs: Callable[[], int]) -> None:
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/tasks",
            json={"request": ("Crie uma API segura e auditável para cadastro de clientes.")},
        )
        assert created.status_code == 202
        drain_jobs()
        pending = client.get(f"/api/v1/tasks/{created.json()['task_id']}").json()
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
        assert approved.status_code == 202
        assert approved.json()["status"] == "RESUMING"

        duplicate_while_queued = client.post(
            f"/api/v1/tasks/{task_id}/human-review",
            json={
                "decision": "REJECT",
                "justification": "A second decision must not be accepted.",
            },
        )
        assert duplicate_while_queued.status_code == 409

        drain_jobs()
        completed = client.get(f"/api/v1/tasks/{task_id}").json()
        assert completed["status"] == "COMPLETED"
        assert completed["human_review"]["status"] == "APPROVED"
        assert completed["human_review"]["reviewer"] == "local-development"
        assert completed["implementation"]
        assert completed["validation"]
        assert completed["judge_evaluation"]["status"] == "COMPLETED"
        assert completed["judge_evaluation"]["authoritative"] is False

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
            event["event_type"] == "HUMAN_REVIEW_DECIDED" and event["actor"] == "local-development"
            for event in events
        )
        assert any(
            event["event_type"] == "JUDGE_EVALUATION" and event["payload"]["authoritative"] is False
            for event in events
        )
        assert any(run["agent_name"] == "llm_judge_agent" for run in audit.json()["agent_runs"])
