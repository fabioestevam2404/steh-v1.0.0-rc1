from collections import Counter
from threading import Lock

_lock = Lock()

_requests: Counter[tuple[str, str, str]] = Counter()


def inc_request(
    method: str,
    path: str,
    status: int,
) -> None:
    """Count an HTTP request. `path` must be a route template to bound cardinality."""
    with _lock:
        _requests[
            (
                method,
                path,
                str(status),
            )
        ] += 1


def render() -> str:
    """Process-local counters of the API process (see app.services.metrics for shared state)."""
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

    return "\n".join(lines) + "\n"
