from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContextKind(StrEnum):
    REQUIREMENTS = "REQUIREMENTS"
    DOCUMENTATION = "DOCUMENTATION"
    POLICY = "POLICY"
    REPOSITORY = "REPOSITORY"


class ContextTrust(StrEnum):
    UNTRUSTED = "UNTRUSTED"
    TRUSTED = "TRUSTED"


class ContextSourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$",
    )
    kind: ContextKind
    version: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1, max_length=200_000)
    priority: int = Field(default=50, ge=0, le=100)
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > 20:
            raise ValueError("Context metadata is limited to 20 entries.")
        if any(len(key) > 64 or len(item) > 256 for key, item in value.items()):
            raise ValueError("Context metadata keys or values are too long.")
        return value


class ContextSourceSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    kind: ContextKind
    version: str
    trust: ContextTrust = ContextTrust.UNTRUSTED
    content: str
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    token_estimate: int = Field(ge=0)
    priority: int = Field(ge=0, le=100)
    metadata: dict[str, str] = Field(default_factory=dict)
    truncated: bool = False
    redacted: bool = False
    suspicious_instruction: bool = False


class ContextSourceReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    kind: ContextKind
    version: str
    trust: ContextTrust
    content_sha256: str
    token_estimate: int
    truncated: bool
    redacted: bool
    suspicious_instruction: bool


class ContextBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    bundle_id: str = Field(pattern=r"^ctx_[0-9a-f]{16}$")
    bundle_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime
    sources: list[ContextSourceSnapshot] = Field(default_factory=list)
    token_estimate: int = Field(ge=0)
    max_tokens: int = Field(gt=0)
    truncated: bool = False


class ContextReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    bundle_id: str
    bundle_sha256: str
    request_sha256: str
    source_count: int = Field(ge=0)
    token_estimate: int = Field(ge=0)
    max_tokens: int = Field(gt=0)
    truncated: bool
    sources: list[ContextSourceReceipt] = Field(default_factory=list)
