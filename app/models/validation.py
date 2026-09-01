from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ValidationStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


class TestEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    status: ValidationStatus
    details: str
    artifact: str | None = None


class ScanFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scanner: str
    rule_id: str
    severity: str
    path: str
    message: str


class ValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tests: list[TestEvidence] = Field(default_factory=list)
    scan_findings: list[ScanFinding] = Field(default_factory=list)
    test_passed: bool
    scanners_passed: bool
    summary: str
