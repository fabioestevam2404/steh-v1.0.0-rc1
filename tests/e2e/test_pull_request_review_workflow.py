from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.github_pull_request import (
    FetchedGitHubPullRequest,
    FetchedPullRequestFile,
    GitHubPullRequestReference,
)
from app.services.github_pull_requests import get_github_pull_request_reader


class FakeGitHubPullRequestReader:
    def fetch(
        self,
        reference: GitHubPullRequestReference,
    ) -> FetchedGitHubPullRequest:
        return FetchedGitHubPullRequest(
            repository=reference.full_name,
            pull_number=reference.pull_number,
            title="Add auditable pull request review",
            body="Review this change without writing to GitHub.",
            state="open",
            author="octocat",
            pull_request_url=(
                f"https://github.com/{reference.full_name}/pull/"
                f"{reference.pull_number}"
            ),
            updated_at=datetime(2026, 9, 5, tzinfo=UTC),
            base_ref="main",
            base_sha="a" * 40,
            head_ref="feature/review",
            head_sha="b" * 40,
            draft=False,
            merged=False,
            changed_files=2,
            additions=20,
            deletions=2,
            files=[
                FetchedPullRequestFile(
                    filename="app/review.py",
                    status="modified",
                    additions=8,
                    deletions=2,
                    changes=10,
                    patch=(
                        "@@ -1,2 +1,8 @@\n"
                        "+password=do-not-store-this-value"
                    ),
                ),
                FetchedPullRequestFile(
                    filename="tests/unit/test_review.py",
                    status="added",
                    additions=12,
                    deletions=0,
                    changes=12,
                    patch="@@ -0,0 +1,12 @@",
                ),
            ],
        )


@pytest.mark.e2e
def test_pull_request_review_is_read_only_context_backed_and_auditable() -> None:
    app.dependency_overrides[
        get_github_pull_request_reader
    ] = FakeGitHubPullRequestReader
    try:
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/tasks/from-github-pull-request",
                json={
                    "pull_request": {
                        "owner": "fabioestevam2404",
                        "repository": "steh-v1.0.0-rc1",
                        "pull_number": 17,
                    }
                },
            )

            assert created.status_code == 201
            payload = created.json()
            assert payload["status"] == "COMPLETED"
            assert payload["source_pull_request"]["pull_number"] == 17
            assert payload["source_pull_request"]["redacted"] is True
            assert payload["pull_request_review"]["recommendation"] == "BLOCK"
            assert payload["pull_request_review"]["requires_human_review"] is True
            assert payload["context"]["source_count"] == 1
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
            assert "pull_request_review_agent" in agent_names
            review_run = next(
                run
                for run in audit_payload["agent_runs"]
                if run["agent_name"] == "pull_request_review_agent"
            )
            assert review_run["findings"]
            assert "GITHUB_PULL_REQUEST_INGESTED" in event_types
            assert "GITHUB_PULL_REQUEST_REVIEWED" in event_types
            assert "CONTEXT_BUNDLE_CREATED" in event_types
            assert "do-not-store-this-value" not in str(audit_payload)
    finally:
        app.dependency_overrides.pop(get_github_pull_request_reader, None)
