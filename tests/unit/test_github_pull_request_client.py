from datetime import UTC, datetime

import httpx
import pytest

from app.models.github_pull_request import GitHubPullRequestReference
from app.services.github_pull_requests import (
    GitHubPullRequestClient,
    GitHubPullRequestRepositoryNotAllowedError,
    GitHubPullRequestUpstreamError,
)


def _reference() -> GitHubPullRequestReference:
    return GitHubPullRequestReference(
        owner="openai",
        repository="steh",
        pull_number=17,
    )


def _metadata() -> dict[str, object]:
    return {
        "number": 17,
        "title": "Add pull request review",
        "body": "Review diffs without changing GitHub.",
        "state": "open",
        "user": {"login": "octocat"},
        "html_url": "https://github.com/openai/steh/pull/17",
        "updated_at": datetime(2026, 9, 5, tzinfo=UTC).isoformat(),
        "base": {"ref": "main", "sha": "a" * 40},
        "head": {"ref": "feature/review", "sha": "b" * 40},
        "draft": False,
        "merged": False,
        "changed_files": 1,
        "additions": 12,
        "deletions": 3,
    }


def _client(transport: httpx.BaseTransport) -> GitHubPullRequestClient:
    return GitHubPullRequestClient(
        base_url="https://api.github.com",
        token="test-token",
        timeout_seconds=5,
        allowed_repositories=frozenset({"openai/steh"}),
        api_version="2026-03-10",
        max_files=50,
        max_response_bytes=100_000,
        transport=transport,
    )


def test_client_reads_fixed_pull_request_paths() -> None:
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        assert request.headers["authorization"] == "Bearer test-token"
        assert request.headers["x-github-api-version"] == "2026-03-10"
        if request.url.path.endswith("/files"):
            assert request.url.params["per_page"] == "50"
            return httpx.Response(
                200,
                json=[
                    {
                        "filename": "app/review.py",
                        "status": "modified",
                        "additions": 12,
                        "deletions": 3,
                        "changes": 15,
                        "patch": "@@ -1 +1 @@",
                    }
                ],
            )
        return httpx.Response(200, json=_metadata())

    pull_request = _client(httpx.MockTransport(handler)).fetch(_reference())

    assert requested_paths == [
        "/repos/openai/steh/pulls/17",
        "/repos/openai/steh/pulls/17/files",
    ]
    assert pull_request.repository == "openai/steh"
    assert pull_request.pull_number == 17
    assert pull_request.files[0].filename == "app/review.py"
    assert pull_request.files_truncated is False


def test_client_blocks_repository_before_request() -> None:
    called = False

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(500)

    client = GitHubPullRequestClient(
        base_url="https://api.github.com",
        token=None,
        timeout_seconds=5,
        allowed_repositories=frozenset({"approved/repository"}),
        api_version="2026-03-10",
        max_files=50,
        max_response_bytes=100_000,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(GitHubPullRequestRepositoryNotAllowedError):
        client.fetch(_reference())

    assert called is False


def test_client_rejects_oversized_response() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, content=b"x" * 101)
    )
    client = GitHubPullRequestClient(
        base_url="https://api.github.com",
        token=None,
        timeout_seconds=5,
        allowed_repositories=frozenset({"openai/steh"}),
        api_version="2026-03-10",
        max_files=50,
        max_response_bytes=100,
        transport=transport,
    )

    with pytest.raises(GitHubPullRequestUpstreamError, match="size limit"):
        client.fetch(_reference())


def test_client_requires_https() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        GitHubPullRequestClient(
            base_url="http://api.github.test",
            token=None,
            timeout_seconds=5,
            allowed_repositories=frozenset({"openai/steh"}),
            api_version="2026-03-10",
            max_files=50,
            max_response_bytes=100_000,
        )


def test_client_enforces_file_limit_even_if_upstream_returns_more() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/files"):
            return httpx.Response(
                200,
                json=[
                    {
                        "filename": f"app/file_{index}.py",
                        "status": "modified",
                        "additions": 1,
                        "deletions": 0,
                        "changes": 1,
                        "patch": "+pass",
                    }
                    for index in range(2)
                ],
            )
        metadata = _metadata()
        metadata["changed_files"] = 2
        return httpx.Response(200, json=metadata)

    client = GitHubPullRequestClient(
        base_url="https://api.github.com",
        token=None,
        timeout_seconds=5,
        allowed_repositories=frozenset({"openai/steh"}),
        api_version="2026-03-10",
        max_files=1,
        max_response_bytes=100_000,
        transport=httpx.MockTransport(handler),
    )

    pull_request = client.fetch(_reference())

    assert len(pull_request.files) == 1
    assert pull_request.files_truncated is True
