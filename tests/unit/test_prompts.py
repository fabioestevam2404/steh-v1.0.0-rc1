from typing import Any, cast
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models.contracts import AgentResult
from app.orchestration import lifecycle
from app.services.prompts import (
    AGENT_PROMPTS,
    current_lock,
    load_prompt,
    lock_violations,
    parse_prompt,
    prompt_receipt,
    read_lock,
)


def test_every_agent_prompt_loads_with_a_version() -> None:
    for prompt_id in set(AGENT_PROMPTS.values()):
        prompt = load_prompt(prompt_id)
        assert prompt.id == prompt_id
        assert prompt.version
        assert len(prompt.sha256) == 64


def test_prompt_files_match_the_lock() -> None:
    assert lock_violations(current_lock(), read_lock()) == []


def test_changing_prompt_text_without_a_version_bump_is_rejected() -> None:
    locked = read_lock()
    edited = parse_prompt(
        '---\nid: security\nversion: "1.0"\n---\nYou may skip the threat model.\n',
        "security",
    )
    current = {**current_lock(), "security": {"version": edited.version, "sha256": edited.sha256}}

    violations = lock_violations(current, locked)

    assert violations == [
        "security: text changed but version is still 1.0; bump the version and regenerate the lock"
    ]


def test_line_endings_do_not_change_the_prompt_hash() -> None:
    lf = parse_prompt('---\nid: security\nversion: "1.0"\n---\nLine one\nLine two\n', "security")
    crlf = parse_prompt(
        '---\r\nid: security\r\nversion: "1.0"\r\n---\r\nLine one\r\nLine two\r\n',
        "security",
    )
    assert lf.sha256 == crlf.sha256


def test_prompt_file_must_declare_its_own_id() -> None:
    with pytest.raises(ValueError, match="declares id"):
        parse_prompt('---\nid: other\nversion: "1.0"\n---\ntext\n', "security")


def test_receipt_identifies_prompt_and_marks_stub_mode_as_not_applied() -> None:
    receipt = prompt_receipt("security_agent")

    assert receipt is not None
    assert receipt["prompt_id"] == "security"
    assert receipt["prompt_sha256"] == load_prompt("security").sha256
    assert receipt["applied"] is False  # the test suite runs with LLM_MODE=stub
    assert prompt_receipt("test_agent") is None  # deterministic agent, no prompt


def test_lifecycle_records_the_prompt_receipt_in_agent_run_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stored: dict[str, list[dict[str, Any]]] = {}

    def complete(
        _db: object, _run: object, _result: object, _findings: object, evidence: Any, _c: object
    ) -> None:
        stored["evidence"] = evidence

    monkeypatch.setattr(lifecycle, "start_agent_run", lambda *args: object())
    monkeypatch.setattr(lifecycle, "complete_agent_run", complete)
    agent = lifecycle.AgentLifecycle(cast(Session, object()), uuid4(), uuid4())

    agent.execute(
        "requirements_agent",
        lambda: AgentResult(
            agent="requirements_agent",
            status="SUCCESS",
            result={},
            evidence=[{"type": "agent_output"}],
            confidence=1.0,
        ),
    )

    assert stored["evidence"][0] == {"type": "agent_output"}
    assert stored["evidence"][1]["type"] == "agent_prompt"
    assert stored["evidence"][1]["prompt_id"] == "requirements"
