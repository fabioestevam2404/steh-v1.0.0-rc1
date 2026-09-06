from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

JudgeArtifactName = Literal[
    "requirements",
    "specification",
    "architecture",
    "security_review",
    "test_plan",
    "implementation",
    "validation",
]


class JudgeDimension(StrEnum):
    REQUIREMENTS = "REQUIREMENTS"
    SPECIFICATION = "SPECIFICATION"
    ARCHITECTURE = "ARCHITECTURE"
    SECURITY = "SECURITY"
    TESTING = "TESTING"
    IMPLEMENTATION = "IMPLEMENTATION"
    VALIDATION = "VALIDATION"


class JudgeEvaluationStatus(StrEnum):
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    UNAVAILABLE = "UNAVAILABLE"


class JudgeVerdict(StrEnum):
    PASS = "PASS"
    CONCERNS = "CONCERNS"
    FAIL = "FAIL"
    NOT_EVALUATED = "NOT_EVALUATED"


class JudgeCriterion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^JUDGE-[A-Z]+-\d{3}$")
    dimension: JudgeDimension
    artifact: JudgeArtifactName
    description: str = Field(min_length=1, max_length=1000)
    weight: float = Field(gt=0, le=1)


class JudgeRubric(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: str = Field(min_length=1, max_length=64)
    pass_score: int = Field(ge=0, le=100)
    concern_score: int = Field(ge=0, le=100)
    criteria: list[JudgeCriterion] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def validate_rubric(self) -> "JudgeRubric":
        if self.concern_score >= self.pass_score:
            raise ValueError("Judge concern score must be lower than pass score.")
        criterion_ids = [item.id for item in self.criteria]
        if len(criterion_ids) != len(set(criterion_ids)):
            raise ValueError("Judge criterion identifiers must be unique.")
        if abs(sum(item.weight for item in self.criteria) - 1.0) > 0.000001:
            raise ValueError("Judge criterion weights must total 1.0.")
        return self


class JudgeInputSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content: str = Field(max_length=200_000)
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    artifact_names: list[JudgeArtifactName] = Field(default_factory=list)
    truncated: bool = False
    redacted: bool = False
    suspicious_instruction: bool = False


class JudgeCriterionProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    criterion_id: str = Field(pattern=r"^JUDGE-[A-Z]+-\d{3}$")
    score: int = Field(ge=0, le=100)
    rationale: str = Field(min_length=1, max_length=2000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=20)


class JudgeProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    criteria: list[JudgeCriterionProposal] = Field(min_length=1, max_length=50)
    summary: str = Field(min_length=1, max_length=3000)
    limitations: list[str] = Field(default_factory=list, max_length=20)


class JudgeCriterionEvaluation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    criterion_id: str
    dimension: JudgeDimension
    description: str
    score: int = Field(ge=0, le=100)
    weight: float = Field(gt=0, le=1)
    weighted_score: float = Field(ge=0, le=100)
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)


class JudgeEvaluationArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    rubric_version: str
    rubric_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: JudgeEvaluationStatus
    verdict: JudgeVerdict
    overall_score: int | None = Field(default=None, ge=0, le=100)
    dimension_scores: dict[JudgeDimension, int] = Field(default_factory=dict)
    criteria: list[JudgeCriterionEvaluation] = Field(default_factory=list)
    summary: str = Field(min_length=1, max_length=3000)
    limitations: list[str] = Field(default_factory=list, max_length=20)
    provider: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=200)
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_truncated: bool
    input_redacted: bool
    output_redacted: bool
    suspicious_instruction: bool
    authoritative: Literal[False] = False
    evaluated_at: datetime
    error_type: str | None = Field(default=None, max_length=200)
