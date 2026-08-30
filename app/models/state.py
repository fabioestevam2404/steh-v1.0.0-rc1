from typing import TypedDict


class EngineeringState(TypedDict, total=False):
    task_id: str
    trace_id: str
    user_request: str
    status: str

    requirements: dict
    requirements_run: dict

    architecture: dict
    architecture_run: dict

    security_review: dict
    security_run: dict
    risk_level: str

    implementation: dict
    implementation_run: dict

    validation: dict
    test_run: dict
    rework_count: int

    evidence: list[dict]
    policy_results: list[dict]
    blocked: bool
