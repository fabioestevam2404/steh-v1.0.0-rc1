import json
import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import TextIO

LOG_FIELDS = (
    "task_id",
    "trace_id",
    "job_id",
    "agent",
    "node",
    "event",
    "duration_ms",
    "status",
    "error_type",
)

# Correlation ids for the unit of work in progress (a request or a job). Values
# are replaced, never mutated, so each context sees its own snapshot.
_log_context: ContextVar[dict[str, str] | None] = ContextVar("steh_log_context", default=None)


def _current_context() -> dict[str, str]:
    return _log_context.get() or {}


@contextmanager
def log_context(**fields: object) -> Iterator[None]:
    """Attach correlation fields to every log record emitted inside the block."""
    values = {key: str(value) for key, value in fields.items() if value is not None}
    token = _log_context.set({**_current_context(), **values})
    try:
        yield
    finally:
        _log_context.reset(token)


class ContextFilter(logging.Filter):
    """Fills missing record fields from the active log context; explicit extras win."""

    def filter(self, record: logging.LogRecord) -> bool:
        for key, value in _current_context().items():
            if getattr(record, key, None) is None:
                setattr(record, key, value)
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for field in LOG_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


def build_handler(stream: TextIO) -> logging.Handler:
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(ContextFilter())
    return handler


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(build_handler(sys.stdout))
    root.setLevel(level.upper())
