from typing import Any, TypedDict


class EngineeringState(TypedDict, total=False):
    task_id: str
    trace_id: str
    user_request: str
    status: str

    requirements: dict[str, Any]
    requirements_run: dict[str, Any]

    architecture: dict[str, Any]
    architecture_run: dict[str, Any]

    security_review: dict[str, Any]
    security_run: dict[str, Any]
    risk_level: str

    implementation: dict[str, Any]
    implementation_run: dict[str, Any]

    validation: dict[str, Any]
    test_run: dict[str, Any]
    rework_count: int

    evidence: list[dict[str, Any]]
    policy_results: list[dict[str, Any]]
    blocked: bool