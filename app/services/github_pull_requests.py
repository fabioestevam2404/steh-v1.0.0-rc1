from collections.abc import Mapping
from typing import Protocol

import httpx

from app.core.config import settings
from app.models.github_pull_request import (
    FetchedGitHubPullRequest,
    FetchedPullRequestFile,
    GitHubPullRequestReference,
)


class GitHubPullRequestError(RuntimeError):
    pass


class GitHubPullRequestNotFoundError(GitHubPullRequestError):
    pass


class GitHubPullRequestRepositoryNotAllowedError(GitHubPullRequestError):
    pass


class GitHubPullRequestUpstreamError(GitHubPullRequestError):
    pass


class GitHubPullRequestReader(Protocol):
    def fetch(
        self,
        reference: GitHubPullRequestReference,
    ) -> FetchedGitHubPullRequest: ...


class GitHubPullRequestClient:
    def __init__(
        self,
        base_url: str,
        token: str | None,
        timeout_seconds: float,
        allowed_repositories: frozenset[str],
        api_version: str,
        max_files: int,
        max_response_bytes: int,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        normalized_url = base_url.rstrip("/")
        if not normalized_url.startswith("https://"):
            raise ValueError("GitHub API URL must use HTTPS.")
        if not 1 <= max_files <= 100:
            raise ValueError("GitHub pull request file limit must be between 1 and 100.")
        if max_response_bytes < 1:
            raise ValueError("GitHub response size limit must be positive.")
        self.base_url = normalized_url
        self.token = token
        self.timeout_seconds = timeout_seconds
        self.allowed_repositories = frozenset(
            item.casefold() for item in allowed_repositories
        )
        self.api_version = api_version
        self.max_files = max_files
        self.max_response_bytes = max_response_bytes
        self.transport = transport

    def _get(self, client: httpx.Client, path: str) -> httpx.Response:
        try:
            with client.stream("GET", path) as response:
                if response.status_code == 404:
                    raise GitHubPullRequestNotFoundError(
                        "GitHub pull request was not found."
                    )
                if response.status_code >= 400:
                    raise GitHubPullRequestUpstreamError(
                        f"GitHub API returned HTTP {response.status_code}."
                    )

                content = bytearray()
                for chunk in response.iter_bytes():
                    if len(content) + len(chunk) > self.max_response_bytes:
                        raise GitHubPullRequestUpstreamError(
                            "GitHub API response exceeded the configured size limit."
                        )
                    content.extend(chunk)
                return httpx.Response(
                    status_code=response.status_code,
                    headers=response.headers,
                    content=bytes(content),
                    request=response.request,
                )
        except GitHubPullRequestError:
            raise
        except httpx.RequestError as exc:
            raise GitHubPullRequestUpstreamError(
                "GitHub API request failed."
            ) from exc

    def fetch(
        self,
        reference: GitHubPullRequestReference,
    ) -> FetchedGitHubPullRequest:
        if reference.full_name.casefold() not in self.allowed_repositories:
            raise GitHubPullRequestRepositoryNotAllowedError(
                f"Repository {reference.full_name!r} is not allowed."
            )

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "STEH-GitHub-PR-Review/1.0",
            "X-GitHub-Api-Version": self.api_version,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        path = (
            f"/repos/{reference.owner}/{reference.repository}"
            f"/pulls/{reference.pull_number}"
        )
        with httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=self.timeout_seconds,
            follow_redirects=False,
            transport=self.transport,
        ) as client:
            metadata_response = self._get(client, path)
            files_response = self._get(
                client,
                f"{path}/files?per_page={self.max_files}",
            )

        try:
            payload = metadata_response.json()
            files_payload = files_response.json()
            if not isinstance(payload, Mapping):
                raise TypeError("Pull request payload must be an object.")
            if not isinstance(files_payload, list):
                raise TypeError("Pull request files payload must be a list.")
            if payload.get("number") != reference.pull_number:
                raise ValueError("Pull request number does not match the request.")

            base = payload.get("base")
            head = payload.get("head")
            user = payload.get("user")
            if not isinstance(base, Mapping) or not isinstance(head, Mapping):
                raise TypeError("Pull request refs are missing.")
            if not isinstance(user, Mapping):
                raise TypeError("Pull request author is missing.")

            selected_files = files_payload[: self.max_files]
            files = [self._parse_file(item) for item in selected_files]
            changed_files = payload["changed_files"]
            if not isinstance(changed_files, int):
                raise TypeError("Pull request changed_files is invalid.")

            return FetchedGitHubPullRequest(
                repository=reference.full_name,
                pull_number=reference.pull_number,
                title=payload["title"],
                body=payload.get("body") or "",
                state=payload["state"],
                author=user["login"],
                pull_request_url=payload["html_url"],
                updated_at=payload["updated_at"],
                base_ref=base["ref"],
                base_sha=base["sha"],
                head_ref=head["ref"],
                head_sha=head["sha"],
                draft=payload["draft"],
                merged=payload["merged"],
                changed_files=changed_files,
                additions=payload["additions"],
                deletions=payload["deletions"],
                files=files,
                files_truncated=(
                    changed_files > len(files)
                    or len(files_payload) > self.max_files
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise GitHubPullRequestUpstreamError(
                "GitHub API returned an invalid pull request payload."
            ) from exc

    @staticmethod
    def _parse_file(payload: object) -> FetchedPullRequestFile:
        if not isinstance(payload, Mapping):
            raise TypeError("Pull request file entry must be an object.")
        patch = payload.get("patch")
        previous_filename = payload.get("previous_filename")
        return FetchedPullRequestFile(
            filename=payload["filename"],
            status=payload["status"],
            additions=payload["additions"],
            deletions=payload["deletions"],
            changes=payload["changes"],
            patch=patch if isinstance(patch, str) else "",
            previous_filename=(
                previous_filename if isinstance(previous_filename, str) else None
            ),
        )


def _allowed_repositories(value: str) -> frozenset[str]:
    return frozenset(item.strip() for item in value.split(",") if item.strip())


def get_github_pull_request_reader() -> GitHubPullRequestReader:
    token = (
        settings.github_token.get_secret_value()
        if settings.github_token is not None
        else None
    )
    return GitHubPullRequestClient(
        base_url=settings.github_api_url,
        token=token or None,
        timeout_seconds=settings.github_timeout_seconds,
        allowed_repositories=_allowed_repositories(
            settings.github_allowed_repositories
        ),
        api_version=settings.github_api_version,
        max_files=settings.github_pr_max_files,
        max_response_bytes=settings.github_pr_max_response_bytes,
    )
