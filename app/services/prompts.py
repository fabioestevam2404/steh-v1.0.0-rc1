"""Versioned agent prompts.

Instructions live in `prompts/<id>.md` with a YAML header (`id`, `version`); the data
an agent sends (requests, artifacts, context) is still assembled in code. Every agent
run records the prompt id, version and SHA-256 in its evidence, and
`prompts/prompts.lock.json` pins the hash of each version so text cannot change
without a version bump.

Regenerate the lock after an intentional change (and a version bump) with
`python -m app.services.prompts --write-lock`.
"""

import hashlib
import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import get_settings

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
LOCK_FILE = PROMPTS_DIR / "prompts.lock.json"

# Agent name (as recorded in agent_runs) -> prompt id.
AGENT_PROMPTS: dict[str, str] = {
    "requirements_agent": "requirements",
    "specification_agent": "specification",
    "architecture_agent": "architecture",
    "security_agent": "security",
    "test_planning_agent": "test_planning",
    "implementation_agent": "implementation",
    "github_issue_analysis_agent": "github_issue_analysis",
    "pull_request_review_agent": "pull_request_review",
    "llm_judge_agent": "llm_judge",
}


class AgentPrompt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z_]+$")
    version: str = Field(min_length=1)
    text: str = Field(min_length=1)

    @property
    def sha256(self) -> str:
        canonical = json.dumps(
            {"id": self.id, "version": self.version, "text": self.text},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_prompt(raw: str, expected_id: str) -> AgentPrompt:
    # Windows checkouts may use CRLF; normalize so the hash depends only on content.
    raw = raw.replace("\r\n", "\n")
    if not raw.startswith("---\n"):
        raise ValueError(f"Prompt {expected_id} must start with a YAML header.")
    header, _, body = raw[len("---\n") :].partition("\n---\n")
    meta = yaml.safe_load(header) or {}
    prompt = AgentPrompt(
        id=meta.get("id", ""), version=str(meta.get("version", "")), text=body.strip()
    )
    if prompt.id != expected_id:
        raise ValueError(f"Prompt file {expected_id}.md declares id {prompt.id!r}.")
    return prompt


@lru_cache
def load_prompt(prompt_id: str) -> AgentPrompt:
    raw = (PROMPTS_DIR / f"{prompt_id}.md").read_text(encoding="utf-8")
    return parse_prompt(raw, prompt_id)


def prompt_receipt(agent_name: str) -> dict[str, Any] | None:
    """Evidence entry identifying the prompt that governs an agent, if it has one."""
    prompt_id = AGENT_PROMPTS.get(agent_name)
    if prompt_id is None:
        return None
    prompt = load_prompt(prompt_id)
    settings = get_settings()
    mode = settings.judge_mode if agent_name == "llm_judge_agent" else settings.llm_mode
    return {
        "type": "agent_prompt",
        "prompt_id": prompt.id,
        "prompt_version": prompt.version,
        "prompt_sha256": prompt.sha256,
        # In stub mode the deterministic stub runs and the prompt is not sent to a model.
        "applied": mode == "openai",
    }


def current_lock() -> dict[str, dict[str, str]]:
    return {
        prompt_id: {
            "version": load_prompt(prompt_id).version,
            "sha256": load_prompt(prompt_id).sha256,
        }
        for prompt_id in sorted(set(AGENT_PROMPTS.values()))
    }


def lock_violations(
    current: dict[str, dict[str, str]],
    locked: dict[str, dict[str, str]],
) -> list[str]:
    """Prompts whose text changed without a version bump, or that are missing from the lock."""
    violations = []
    for prompt_id, entry in sorted(current.items()):
        pinned = locked.get(prompt_id)
        if pinned is None:
            violations.append(f"{prompt_id}: not in {LOCK_FILE.name}")
        elif pinned["version"] == entry["version"] and pinned["sha256"] != entry["sha256"]:
            violations.append(
                f"{prompt_id}: text changed but version is still {entry['version']}; "
                "bump the version and regenerate the lock"
            )
        elif pinned != entry:
            violations.append(f"{prompt_id}: lock is outdated; regenerate it")
    return violations


def read_lock() -> dict[str, dict[str, str]]:
    locked: dict[str, dict[str, str]] = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    return locked


def main(argv: list[str]) -> int:
    if argv == ["--check"]:
        violations = lock_violations(current_lock(), read_lock())
        for violation in violations:
            print(violation, file=sys.stderr)
        return 1 if violations else 0
    if argv == ["--write-lock"]:
        load_prompt.cache_clear()
        LOCK_FILE.write_text(json.dumps(current_lock(), indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {LOCK_FILE}")
        return 0
    print("usage: python -m app.services.prompts [--check | --write-lock]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
