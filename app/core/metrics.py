from collections import Counter
from threading import Lock

_lock = Lock()
_requests = Counter()
_workflows = Counter()

def inc_request(method: str, path: str, status: int) -> None:
    with _lock:
        _requests[(method, path, str(status))] += 1

def inc_workflow(status: str) -> None:
    with _lock:
        _workflows[status] += 1

def render() -> str:
    lines = [
        "# HELP steh_http_requests_total HTTP requests.",
        "# TYPE steh_http_requests_total counter",
    ]
    with _lock:
        for (method,path,status),value in sorted(_requests.items()):
            lines.append(
                f'steh_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {value}'
            )
        lines += [
            "# HELP steh_workflows_total Workflow terminal states.",
            "# TYPE steh_workflows_total counter",
        ]
        for status,value in sorted(_workflows.items()):
            lines.append(f'steh_workflows_total{{status="{status}"}} {value}')
    return "\n".join(lines) + "\n"
