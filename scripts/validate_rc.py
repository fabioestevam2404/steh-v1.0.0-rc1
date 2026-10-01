import argparse
import json
import os
import platform
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

RELEASE_VERSION = (Path(__file__).parents[1] / "VERSION").read_text(encoding="utf-8").strip()
SCANNER_IMAGE = f"steh-scanner:{RELEASE_VERSION}"


class Gate(TypedDict):
    id: str
    name: str
    command: list[str]


class GateResult(TypedDict):
    id: str
    name: str
    command: list[str]
    status: str
    return_code: int
    duration_seconds: float


GATES: list[Gate] = [
    {
        "id": "RC-01",
        "name": "Python source compiles",
        "command": [sys.executable, "-m", "compileall", "-q", "app"],
    },
    {
        "id": "RC-02",
        "name": "Alembic upgrades clean database",
        "command": [sys.executable, "-m", "alembic", "upgrade", "head"],
    },
    {
        "id": "RC-03A",
        "name": "Alembic downgrades to base",
        "command": [sys.executable, "-m", "alembic", "downgrade", "base"],
    },
    {
        "id": "RC-03B",
        "name": "Alembic restores head",
        "command": [sys.executable, "-m", "alembic", "upgrade", "head"],
    },
    {
        "id": "RC-04",
        "name": "Unit tests pass",
        "command": [sys.executable, "-m", "pytest", "tests/unit", "-q"],
    },
    {
        "id": "RC-05",
        "name": "Integration tests pass",
        "command": [sys.executable, "-m", "pytest", "tests/integration", "-q"],
    },
    {
        "id": "RC-06",
        "name": "End-to-end tests pass",
        "command": [sys.executable, "-m", "pytest", "tests/e2e", "-q"],
    },
    {
        "id": "RC-07",
        "name": "Agent lifecycle is auditable",
        "command": [sys.executable, "-m", "pytest", "tests/unit/test_lifecycle.py", "-q"],
    },
    {
        "id": "RC-08/09",
        "name": "Authentication and authorization boundaries pass",
        "command": [sys.executable, "-m", "pytest", "tests/unit/test_auth.py", "-q"],
    },
    {
        "id": "RC-10",
        "name": "Health and readiness checks pass",
        "command": [sys.executable, "-m", "pytest", "tests/integration/test_health.py", "-q"],
    },
    {
        "id": "RC-11",
        "name": "Operational metrics pass",
        "command": [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_metrics.py",
            "tests/integration/test_task_jobs.py::test_queue_metrics_reflect_database_state",
            "-q",
        ],
    },
    {
        "id": "RC-13",
        "name": "Scanner isolation passes",
        "command": [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_process_runner.py",
            "tests/unit/test_scanner_suite.py",
            "-q",
        ],
    },
    {
        "id": "RC-17",
        "name": "Specification, traceability and test-plan gates pass",
        "command": [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_specification_agent.py",
            "tests/unit/test_test_planning_agent.py",
            "tests/unit/test_policy_engine.py",
            "tests/unit/test_policy_loader.py",
            "-q",
        ],
    },
    {
        "id": "RC-18",
        "name": "Bounded rework terminates deterministically",
        "command": [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_rework_controller.py",
            "tests/unit/test_rework_graph.py",
            "-q",
        ],
    },
    {
        "id": "RC-19",
        "name": "Human review resumes once and expires safely",
        "command": [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_human_review.py",
            "tests/unit/test_graph.py::test_rejected_human_review_blocks_from_checkpoint",
            "tests/unit/test_graph.py::test_expired_review_blocks_before_implementation",
            "tests/e2e/test_human_review_workflow.py",
            "-q",
        ],
    },
    {
        "id": "RC-20",
        "name": "Context Engine redacts and labels untrusted input",
        "command": [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_context_engine.py",
            "tests/e2e/test_context_workflow.py",
            "-q",
        ],
    },
    {
        "id": "RC-21",
        "name": "GitHub issue analysis is read-only and allowlisted",
        "command": [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_github_client.py",
            "tests/unit/test_github_issue_agent.py",
            "tests/e2e/test_github_issue_workflow.py",
            "-q",
        ],
    },
    {
        "id": "RC-22",
        "name": "Pull request review is read-only with deterministic safeguards",
        "command": [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_github_pull_request_client.py",
            "tests/unit/test_pull_request_review_agent.py",
            "tests/e2e/test_pull_request_review_workflow.py",
            "-q",
        ],
    },
    {
        "id": "RC-23",
        "name": "LLM judge is non-authoritative",
        "command": [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_llm_judge.py",
            "tests/unit/test_graph.py::test_disabled_judge_does_not_change_completed_status",
            "tests/unit/test_graph.py::test_unavailable_judge_does_not_change_completed_status",
            "tests/unit/test_graph.py::test_failing_judge_verdict_does_not_change_completed_status",
            "-q",
        ],
    },
    {
        "id": "RC-24",
        "name": "Asynchronous queue is durable, recovers from checkpoints and fails closed",
        "command": [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_job_recovery.py",
            "tests/integration/test_task_jobs.py",
            "tests/e2e/test_task_workflow.py",
            "-q",
        ],
    },
    {
        "id": "RC-25",
        "name": "Structured logs carry correlation ids",
        "command": [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_logging.py",
            "-q",
        ],
    },
    {
        "id": "RC-26",
        "name": "Agent prompts are versioned, pinned and recorded",
        "command": [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_prompts.py",
            "-q",
        ],
    },
    {
        "id": "RC-26B",
        "name": "Prompt lock matches prompt files",
        "command": [sys.executable, "-m", "app.services.prompts", "--check"],
    },
    {"id": "RC-14", "name": "Ruff passes", "command": [sys.executable, "-m", "ruff", "check", "."]},
    {
        "id": "RC-14B",
        "name": "Ruff format passes",
        "command": [sys.executable, "-m", "ruff", "format", "--check", "."],
    },
    {"id": "RC-15", "name": "mypy passes", "command": [sys.executable, "-m", "mypy", "app"]},
    {
        "id": "RC-12A",
        "name": "Scanner image builds",
        "command": ["docker", "build", "-f", "scanner.Dockerfile", "-t", SCANNER_IMAGE, "."],
    },
    {
        "id": "RC-12B",
        "name": "Gitleaks is executable",
        "command": ["docker", "run", "--rm", SCANNER_IMAGE, "gitleaks", "version"],
    },
    {
        "id": "RC-12C",
        "name": "Trivy is executable",
        "command": ["docker", "run", "--rm", SCANNER_IMAGE, "trivy", "--version"],
    },
    {
        "id": "RC-12D",
        "name": "Semgrep is executable",
        "command": ["docker", "run", "--rm", SCANNER_IMAGE, "semgrep", "--version"],
    },
]


def _git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=False, capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def run_gate(gate: Gate) -> GateResult:
    print(f"\n== {gate['id']} | {gate['name']} ==", flush=True)
    started = time.perf_counter()
    try:
        completed = subprocess.run(gate["command"], check=False)
        return_code = completed.returncode
    except OSError as exc:
        print(f"Unable to execute gate: {exc}", file=sys.stderr, flush=True)
        return_code = 127

    return {
        **gate,
        "status": "PASS" if return_code == 0 else "FAIL",
        "return_code": return_code,
        "duration_seconds": round(time.perf_counter() - started, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the STEH release candidate.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/rc-validation-evidence.json"),
    )
    parser.add_argument(
        "--allow-database-reset",
        action="store_true",
        help="Allow the destructive Alembic downgrade-to-base validation.",
    )
    args = parser.parse_args()
    if not args.allow_database_reset:
        parser.error(
            "RC validation resets the configured database; "
            "use --allow-database-reset only with an isolated database."
        )
    started_at = datetime.now(UTC)
    results = [run_gate(gate) for gate in GATES]
    passed = all(result["status"] == "PASS" for result in results)
    completed_at = datetime.now(UTC)

    evidence = {
        "schema_version": "1.0",
        "release_candidate": RELEASE_VERSION,
        "status": "PASS" if passed else "FAIL",
        "commit": _git_commit(),
        "run_id": os.getenv("GITHUB_RUN_ID"),
        "run_attempt": os.getenv("GITHUB_RUN_ATTEMPT"),
        "repository": os.getenv("GITHUB_REPOSITORY"),
        "runner_os": os.getenv("RUNNER_OS", platform.system()),
        "python_version": platform.python_version(),
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_seconds": round((completed_at - started_at).total_seconds(), 3),
        "gates": results,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"\nEvidence written to {args.output}")
    print(f"RC validation: {evidence['status']}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
