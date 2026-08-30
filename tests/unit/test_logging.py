import json
import logging

from app.core.logging import JsonFormatter


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
