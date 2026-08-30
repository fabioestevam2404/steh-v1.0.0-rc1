from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict


class PolicyRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    description: str
    check: str
    action: str


class PolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    rules: list[PolicyRule]


def load_policy_config(path: str) -> PolicyConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return PolicyConfig.model_validate(raw)
