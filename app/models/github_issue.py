from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

GitHubLabel = Annotated[str, Field(min_length=1, max_length=100)]


class GitHubIssueReference(BaseModel):
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
    issue_number: int = Field(ge=1)

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repository}"


class GitHubIssueTaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue: GitHubIssueReference


class FetchedGitHubIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repository: str = Field(min_length=3, max_length=140)
    issue_number: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=512)
    body: str = Field(default="", max_length=100_000)
    state: Literal["open", "closed"]
    labels: list[GitHubLabel] = Field(default_factory=list, max_length=50)
    author: str = Field(min_length=1, max_length=128)
    issue_url: str = Field(
        min_length=1,
        max_length=2048,
        pattern=r"^https://",
    )
    updated_at: datetime


class GitHubIssueSnapshot(FetchedGitHubIssue):
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    redacted: bool = False
    suspicious_instruction: bool = False
    truncated: bool = False


class GitHubIssueReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    repository: str
    issue_number: int
    state: Literal["open", "closed"]
    labels: list[GitHubLabel] = Field(default_factory=list)
    issue_url: str = Field(pattern=r"^https://")
    updated_at: datetime
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    redacted: bool
    suspicious_instruction: bool
    truncated: bool


class IssueKind(StrEnum):
    BUG = "BUG"
    FEATURE = "FEATURE"
    SECURITY = "SECURITY"
    DOCUMENTATION = "DOCUMENTATION"
    MAINTENANCE = "MAINTENANCE"
    UNKNOWN = "UNKNOWN"


class IssuePriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IssueRecommendation(StrEnum):
    PROCEED = "PROCEED"
    CLARIFY = "CLARIFY"
    BLOCK = "BLOCK"


class IssueAnalysisArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    repository: str
    issue_number: int
    issue_url: str = Field(pattern=r"^https://")
    issue_updated_at: datetime
    source_content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    summary: str = Field(min_length=1, max_length=1000)
    problem_statement: str = Field(min_length=1, max_length=5000)
    issue_kind: IssueKind
    priority: IssuePriority
    functional_requirements: list[str] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    recommendation: IssueRecommendation
