import io
import json
import logging
from typing import Any, cast
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.core.logging import JsonFormatter, build_handler, log_context
from app.models.contracts import AgentResult
from app.orchestration import lifecycle


def test_json_formatter_includes_trace_fields() -> None:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="done",
        args=(),
        exc_info=None,
    )
    record.task_id = "task-1"
    record.trace_id = "trace-1"
    record.status = "SUCCESS"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["task_id"] == "task-1"
    assert payload["trace_id"] == "trace-1"
    assert payload["status"] == "SUCCESS"


def _capture(logger_name: str) -> tuple[logging.Logger, io.StringIO, logging.Handler]:
    stream = io.StringIO()
    handler = build_handler(stream)
    logger = logging.getLogger(logger_name)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger, stream, handler


def _lines(stream: io.StringIO) -> list[dict[str, Any]]:
    return [json.loads(line) for line in stream.getvalue().splitlines()]


def test_log_context_injects_correlation_ids_and_explicit_extra_wins() -> None:
    logger, stream, handler = _capture("test.context")
    try:
        with log_context(task_id="task-1", trace_id="trace-1"):
            with log_context(job_id="job-1"):
                logger.info("inside", extra={"event": "inside"})
            logger.info("override", extra={"task_id": "explicit"})
        logger.info("outside")
    finally:
        logger.removeHandler(handler)

    inside, override, outside = _lines(stream)
    assert inside["task_id"] == "task-1"
    assert inside["trace_id"] == "trace-1"
    assert inside["job_id"] == "job-1"
    assert override["task_id"] == "explicit"
    assert "job_id" not in override
    assert "task_id" not in outside


def test_agent_lifecycle_logs_start_completion_and_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(lifecycle, "start_agent_run", lambda *args: object())
    monkeypatch.setattr(lifecycle, "complete_agent_run", lambda *args: None)
    monkeypatch.setattr(lifecycle, "fail_agent_run", lambda *args: None)
    task_id, trace_id = uuid4(), uuid4()
    agent = lifecycle.AgentLifecycle(cast(Session, object()), task_id, trace_id)

    logger, stream, handler = _capture("steh.agents")
    try:
        agent.execute(
            "requirements_agent",
            lambda: AgentResult(
                agent="requirements_agent", status="SUCCESS", result={}, confidence=1.0
            ),
        )

        def boom() -> AgentResult:
            raise RuntimeError("model unavailable")

        with pytest.raises(RuntimeError):
            agent.execute("security_agent", boom)
    finally:
        logger.removeHandler(handler)

    started, completed, failed_started, failed = _lines(stream)
    assert started["event"] == "agent_started"
    assert completed["event"] == "agent_completed"
    assert completed["agent"] == "requirements_agent"
    assert completed["status"] == "SUCCEEDED"
    assert completed["duration_ms"] >= 0
    assert failed_started["agent"] == "security_agent"
    assert failed["event"] == "agent_failed"
    assert failed["level"] == "ERROR"
    assert failed["error_type"] == "RuntimeError"
    assert "model unavailable" not in json.dumps(failed)
    for line in (started, completed, failed):
        assert line["task_id"] == str(task_id)
        assert line["trace_id"] == str(trace_id)
