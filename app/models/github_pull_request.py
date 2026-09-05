from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PullRequestFileStatus = Literal[
    "added",
    "changed",
    "copied",
    "modified",
    "removed",
    "renamed",
    "unchanged",
]


class GitHubPullRequestReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    owner: str = Field(
        min_length=1,
        max_length=39,
        pattern=r"^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$",
    )
    repository: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9._-]+$",
    )
    pull_number: int = Field(ge=1)

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repository}"


class GitHubPullRequestTaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pull_request: GitHubPullRequestReference


class FetchedPullRequestFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    filename: str = Field(min_length=1, max_length=1024)
    status: PullRequestFileStatus
    additions: int = Field(ge=0)
    deletions: int = Field(ge=0)
    changes: int = Field(ge=0)
    patch: str = Field(default="", max_length=500_000)
    previous_filename: str | None = Field(default=None, max_length=1024)


class FetchedGitHubPullRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repository: str = Field(min_length=3, max_length=140)
    pull_number: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=512)
    body: str = Field(default="", max_length=100_000)
    state: Literal["open", "closed"]
    author: str = Field(min_length=1, max_length=128)
    pull_request_url: str = Field(
        min_length=1,
        max_length=2048,
        pattern=r"^https://",
    )
    updated_at: datetime
    base_ref: str = Field(min_length=1, max_length=255)
    base_sha: str = Field(pattern=r"^[0-9a-fA-F]{7,64}$")
    head_ref: str = Field(min_length=1, max_length=255)
    head_sha: str = Field(pattern=r"^[0-9a-fA-F]{7,64}$")
    draft: bool
    merged: bool
    changed_files: int = Field(ge=0)
    additions: int = Field(ge=0)
    deletions: int = Field(ge=0)
    files: list[FetchedPullRequestFile] = Field(default_factory=list, max_length=100)
    files_truncated: bool = False


class PullRequestFileSnapshot(FetchedPullRequestFile):
    patch_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    redacted: bool = False
    suspicious_instruction: bool = False
    truncated: bool = False


class GitHubPullRequestSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repository: str = Field(min_length=3, max_length=140)
    pull_number: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=512)
    body: str = Field(default="", max_length=100_000)
    state: Literal["open", "closed"]
    author: str = Field(min_length=1, max_length=128)
    pull_request_url: str = Field(pattern=r"^https://")
    updated_at: datetime
    base_ref: str = Field(min_length=1, max_length=255)
    base_sha: str = Field(pattern=r"^[0-9a-fA-F]{7,64}$")
    head_ref: str = Field(min_length=1, max_length=255)
    head_sha: str = Field(pattern=r"^[0-9a-fA-F]{7,64}$")
    draft: bool
    merged: bool
    changed_files: int = Field(ge=0)
    additions: int = Field(ge=0)
    deletions: int = Field(ge=0)
    files: list[PullRequestFileSnapshot] = Field(default_factory=list, max_length=100)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    redacted: bool = False
    suspicious_instruction: bool = False
    truncated: bool = False


class GitHubPullRequestReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repository: str
    pull_number: int
    state: Literal["open", "closed"]
    pull_request_url: str = Field(pattern=r"^https://")
    updated_at: datetime
    base_ref: str
    base_sha: str
    head_ref: str
    head_sha: str
    draft: bool
    merged: bool
    changed_files: int = Field(ge=0)
    fetched_files: int = Field(ge=0)
    additions: int = Field(ge=0)
    deletions: int = Field(ge=0)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    redacted: bool
    suspicious_instruction: bool
    truncated: bool


class PullRequestRisk(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PullRequestRecommendation(StrEnum):
    READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"
    CHANGES_REQUIRED = "CHANGES_REQUIRED"
    BLOCK = "BLOCK"


class PullRequestFindingCategory(StrEnum):
    ARCHITECTURE = "ARCHITECTURE"
    CONTRACT = "CONTRACT"
    DOCUMENTATION = "DOCUMENTATION"
    QUALITY = "QUALITY"
    SECURITY = "SECURITY"
    TESTING = "TESTING"


class PullRequestFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    severity: PullRequestRisk
    category: PullRequestFindingCategory
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=2000)
    file_path: str | None = Field(default=None, max_length=1024)
    line: int | None = Field(default=None, ge=1)
    recommendation: str = Field(min_length=1, max_length=2000)


class PullRequestReviewArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    repository: str
    pull_number: int
    pull_request_url: str = Field(pattern=r"^https://")
    pull_request_updated_at: datetime
    source_content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    context_bundle_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    summary: str = Field(min_length=1, max_length=1000)
    change_intent: str = Field(min_length=1, max_length=5000)
    changed_components: list[str] = Field(default_factory=list, max_length=100)
    findings: list[PullRequestFinding] = Field(default_factory=list, max_length=100)
    test_coverage_assessment: str = Field(min_length=1, max_length=3000)
    security_assessment: str = Field(min_length=1, max_length=3000)
    architecture_assessment: str = Field(min_length=1, max_length=3000)
    risk_level: PullRequestRisk
    recommendation: PullRequestRecommendation
    requires_human_review: Literal[True] = True
