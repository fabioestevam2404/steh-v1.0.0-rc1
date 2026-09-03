from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class HumanDecision(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class HumanReviewStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class HumanReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: HumanDecision
    justification: str = Field(min_length=10, max_length=2000)


class HumanReviewResume(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: HumanReviewStatus
    reviewer: str = Field(min_length=1)
    justification: str = Field(min_length=1, max_length=2000)
    decided_at: datetime


class HumanReviewArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: HumanReviewStatus
    requested_at: datetime
    expires_at: datetime
    policy_result_count: int = Field(ge=0)
    reviewer: str | None = None
    justification: str | None = None
    decided_at: datetime | None = None
