from collections.abc import Mapping
from typing import Protocol

import httpx

from app.core.config import settings
from app.models.github_issue import FetchedGitHubIssue, GitHubIssueReference


class GitHubIssueError(RuntimeError):
    pass


class GitHubRepositoryNotAllowedError(GitHubIssueError):
    pass


class GitHubIssueNotFoundError(GitHubIssueError):
    pass


class GitHubPullRequestUnsupportedError(GitHubIssueError):
    pass


class GitHubUpstreamError(GitHubIssueError):
    pass


class GitHubIssueReader(Protocol):
    def fetch(self, reference: GitHubIssueReference) -> FetchedGitHubIssue: ...


class GitHubIssueClient:
    def __init__(
        self,
        base_url: str,
        token: str | None,
        timeout_seconds: float,
        allowed_repositories: frozenset[str],
        api_version: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        normalized_url = base_url.rstrip("/")
        if not normalized_url.startswith("https://"):
            raise ValueError("GitHub API URL must use HTTPS.")
        self.base_url = normalized_url
        self.token = token
        self.timeout_seconds = timeout_seconds
        self.allowed_repositories = frozenset(
            item.casefold() for item in allowed_repositories
        )
        self.api_version = api_version
        self.transport = transport

    def fetch(self, reference: GitHubIssueReference) -> FetchedGitHubIssue:
        if reference.full_name.casefold() not in self.allowed_repositories:
            raise GitHubRepositoryNotAllowedError(
                f"Repository {reference.full_name!r} is not allowed."
            )

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "STEH-GitHub-Issue-Analysis/1.0",
            "X-GitHub-Api-Version": self.api_version,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            with httpx.Client(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout_seconds,
                follow_redirects=False,
                transport=self.transport,
            ) as client:
                response = client.get(
                    f"/repos/{reference.owner}/{reference.repository}"
                    f"/issues/{reference.issue_number}"
                )
        except httpx.RequestError as exc:
            raise GitHubUpstreamError("GitHub API request failed.") from exc

        if response.status_code == 404:
            raise GitHubIssueNotFoundError("GitHub issue was not found.")
        if response.status_code >= 400:
            raise GitHubUpstreamError(
                f"GitHub API returned HTTP {response.status_code}."
            )

        try:
            payload = response.json()
            if not isinstance(payload, Mapping):
                raise TypeError("GitHub issue payload must be an object.")
            if "pull_request" in payload:
                raise GitHubPullRequestUnsupportedError(
                    "The requested resource is a pull request, not an issue."
                )
            labels_payload = payload.get("labels", [])
            labels = [
                str(item.get("name"))
                for item in labels_payload
                if isinstance(item, Mapping) and item.get("name")
            ]
            user = payload.get("user")
            author = user.get("login") if isinstance(user, Mapping) else None
            if not isinstance(author, str):
                raise TypeError("GitHub issue author is missing.")
            return FetchedGitHubIssue(
                repository=reference.full_name,
                issue_number=reference.issue_number,
                title=payload["title"],
                body=payload.get("body") or "",
                state=payload["state"],
                labels=labels,
                author=author,
                issue_url=payload["html_url"],
                updated_at=payload["updated_at"],
            )
        except GitHubPullRequestUnsupportedError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise GitHubUpstreamError("GitHub API returned an invalid issue payload.") from exc


def _allowed_repositories(value: str) -> frozenset[str]:
    return frozenset(item.strip() for item in value.split(",") if item.strip())


def get_github_issue_reader() -> GitHubIssueReader:
    token = (
        settings.github_token.get_secret_value()
        if settings.github_token is not None
        else None
    )
    return GitHubIssueClient(
        base_url=settings.github_api_url,
        token=token or None,
        timeout_seconds=settings.github_timeout_seconds,
        allowed_repositories=_allowed_repositories(
            settings.github_allowed_repositories
        ),
        api_version=settings.github_api_version,
    )
