from collections import Counter
from threading import Lock

_lock = Lock()

_requests: Counter[tuple[str, str, str]] = Counter()
_workflows: Counter[str] = Counter()


def inc_request(
    method: str,
    path: str,
    status: int,
) -> None:
    with _lock:
        _requests[
            (
                method,
                path,
                str(status),
            )
        ] += 1


def inc_workflow(status: str) -> None:
    with _lock:
        _workflows[status] += 1


def render() -> str:
    lines = [
        "# HELP steh_http_requests_total HTTP requests.",
        "# TYPE steh_http_requests_total counter",
    ]

    with _lock:
        for (
            method,
            path,
            status,
        ), value in sorted(_requests.items()):
            metric = (
                "steh_http_requests_total"
                f'{{method="{method}",'
                f'path="{path}",'
                f'status="{status}"}} '
                f"{value}"
            )
            lines.append(metric)

        lines += [
            (
                "# HELP steh_workflows_total "
                "Workflow terminal states."
            ),
            "# TYPE steh_workflows_total counter",
        ]

        for status, value in sorted(_workflows.items()):
            lines.append(
                "steh_workflows_total"
                f'{{status="{status}"}} '
                f"{value}"
            )

    return "\n".join(lines) + "\n"