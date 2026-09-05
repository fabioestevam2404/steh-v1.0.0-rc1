from datetime import UTC, datetime

import httpx
import pytest

from app.models.github_issue import GitHubIssueReference
from app.services.github_client import (
    GitHubIssueClient,
    GitHubPullRequestUnsupportedError,
    GitHubRepositoryNotAllowedError,
)


def _reference() -> GitHubIssueReference:
    return GitHubIssueReference(
        owner="openai",
        repository="steh",
        issue_number=42,
    )


def test_client_builds_fixed_github_api_path_and_parses_issue() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == httpx.URL(
            "https://api.github.com/repos/openai/steh/issues/42"
        )
        assert request.headers["authorization"] == "Bearer test-token"
        assert request.headers["x-github-api-version"] == "2026-03-10"
        return httpx.Response(
            200,
            json={
                "title": "Add issue analysis",
                "body": "Create a read-only issue intake flow.",
                "state": "open",
                "labels": [{"name": "enhancement"}],
                "user": {"login": "octocat"},
                "html_url": "https://github.com/openai/steh/issues/42",
                "updated_at": datetime(2026, 9, 5, tzinfo=UTC).isoformat(),
            },
        )

    client = GitHubIssueClient(
        base_url="https://api.github.com",
        token="test-token",
        timeout_seconds=5,
        allowed_repositories=frozenset({"openai/steh"}),
        api_version="2026-03-10",
        transport=httpx.MockTransport(handler),
    )

    issue = client.fetch(_reference())

    assert issue.repository == "openai/steh"
    assert issue.issue_number == 42
    assert issue.labels == ["enhancement"]


def test_client_blocks_repository_outside_allowlist_before_request() -> None:
    client = GitHubIssueClient(
        base_url="https://api.github.com",
        token=None,
        timeout_seconds=5,
        allowed_repositories=frozenset({"approved/repository"}),
        api_version="2026-03-10",
    )

    with pytest.raises(GitHubRepositoryNotAllowedError):
        client.fetch(_reference())


def test_client_rejects_pull_request_payload() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            json={"pull_request": {"url": "https://api.github.com/pulls/42"}},
        )
    )
    client = GitHubIssueClient(
        base_url="https://api.github.com",
        token=None,
        timeout_seconds=5,
        allowed_repositories=frozenset({"openai/steh"}),
        api_version="2026-03-10",
        transport=transport,
    )

    with pytest.raises(GitHubPullRequestUnsupportedError):
        client.fetch(_reference())
