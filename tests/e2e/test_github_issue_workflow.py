from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.github_issue import FetchedGitHubIssue, GitHubIssueReference
from app.services.github_client import get_github_issue_reader


class FakeGitHubIssueReader:
    def fetch(self, reference: GitHubIssueReference) -> FetchedGitHubIssue:
        return FetchedGitHubIssue(
            repository=reference.full_name,
            issue_number=reference.issue_number,
            title="Add auditable GitHub issue intake",
            body="Create a read-only flow. password=do-not-store-this-value",
            state="open",
            labels=["enhancement"],
            author="octocat",
            issue_url=(
                f"https://github.com/{reference.full_name}/issues/"
                f"{reference.issue_number}"
            ),
            updated_at=datetime(2026, 9, 5, tzinfo=UTC),
        )


@pytest.mark.e2e
def test_github_issue_creates_auditable_context_backed_task() -> None:
    app.dependency_overrides[get_github_issue_reader] = FakeGitHubIssueReader
    try:
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/tasks/from-github-issue",
                json={
                    "issue": {
                        "owner": "fabioestevam2404",
                        "repository": "steh-v1.0.0-rc1",
                        "issue_number": 42,
                    }
                },
            )

            assert created.status_code == 201
            payload = created.json()
            assert payload["status"] == "HUMAN_REVIEW"
            assert payload["source_issue"]["issue_number"] == 42
            assert payload["source_issue"]["redacted"] is True
            assert payload["issue_analysis"]["issue_kind"] == "FEATURE"
            assert payload["context"]["source_count"] == 2
            assert "do-not-store-this-value" not in str(payload)

            audit = client.get(f"/api/v1/tasks/{payload['task_id']}/audit")
            assert audit.status_code == 200
            audit_payload = audit.json()
            agent_names = {
                run["agent_name"] for run in audit_payload["agent_runs"]
            }
            event_types = {
                event["event_type"] for event in audit_payload["events"]
            }
            assert "github_issue_analysis_agent" in agent_names
            assert "GITHUB_ISSUE_INGESTED" in event_types
            assert "GITHUB_ISSUE_ANALYZED" in event_types
            assert "do-not-store-this-value" not in str(audit_payload)
    finally:
        app.dependency_overrides.pop(get_github_issue_reader, None)
