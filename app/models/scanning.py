from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScannerEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scanner: str
    success: bool
    exit_code: int | None = None
    duration_ms: float
    findings: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class ReworkDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required: bool
    attempt: int
    max_attempts: int
    exhausted: bool
    reasons: list[str] = Field(default_factory=list)