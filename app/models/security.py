from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class Severity(StrEnum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FindingStatus(StrEnum):
    OPEN = "OPEN"
    ACCEPTED = "ACCEPTED"
    MITIGATED = "MITIGATED"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class SecurityFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: UUID = Field(default_factory=uuid4)
    title: str
    description: str
    severity: Severity
    category: str
    affected_component: str
    threat: str
    recommendation: str
    evidence: list[str] = Field(default_factory=list)
    status: FindingStatus = FindingStatus.OPEN


class Threat(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    description: str
    affected_asset: str
    attack_surface: str
    mitigation: str


class ThreatModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assets: list[str] = Field(default_factory=list)
    trust_boundaries: list[str] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)
    threats: list[Threat] = Field(default_factory=list)
    controls: list[str] = Field(default_factory=list)
    residual_risks: list[str] = Field(default_factory=list)
    security_requirements: list[str] = Field(default_factory=list)


class SecurityReviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    threat_model: ThreatModel
    findings: list[SecurityFinding] = Field(default_factory=list)
    overall_risk: Severity
    summary: str
