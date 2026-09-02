from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class TaskStatus(StrEnum):
    CREATED = "CREATED"
    ANALYZING = "ANALYZING"
    ARCHITECTING = "ARCHITECTING"
    IMPLEMENTING = "IMPLEMENTING"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    BLOCKED = "BLOCKED"
    REWORK_REQUIRED = "REWORK_REQUIRED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: str = Field(min_length=10, max_length=10000)


class RequirementsResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    functional_requirements: list[str] = Field(default_factory=list)
    non_functional_requirements: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class ArchitectureComponent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    responsibility: str
    technology_options: list[str] = Field(default_factory=list)


class ArchitectureDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    decision: str
    rationale: str
    tradeoffs: list[str] = Field(default_factory=list)


class ArchitectureResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    architecture_style: str
    components: list[ArchitectureComponent] = Field(default_factory=list)
    data_flow: list[str] = Field(default_factory=list)
    security_considerations: list[str] = Field(default_factory=list)
    scalability_considerations: list[str] = Field(default_factory=list)
    observability_considerations: list[str] = Field(default_factory=list)
    decisions: list[ArchitectureDecision] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class AgentResult(BaseModel):
    agent: str
    status: str
    result: dict[str, Any]
    findings: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class TaskResponse(BaseModel):
    task_id: UUID
    trace_id: UUID
    status: TaskStatus
    requirements: RequirementsResult | None = None
    architecture: ArchitectureResult | None = None
    security_review: dict[str, Any] | None = None
    risk_level: str | None = None
    implementation: dict[str, Any] | None = None
    validation: dict[str, Any] | None = None
    rework_count: int = 0
    external_scan: list[dict[str, Any]] | None = None
    rework_decision: dict[str, Any] | None = None
    created_at: datetime


def ids() -> tuple[UUID, UUID]:
    return uuid4(), uuid4()


def utc_now() -> datetime:
    return datetime.now(UTC)