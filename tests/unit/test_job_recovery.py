from collections import Counter
from datetime import UTC, datetime
from typing import Any

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.agents.architecture import ArchitectureAgent
from app.agents.requirements import RequirementsAgent
from app.orchestration.graph import build_graph
from app.services.tasks import invoke_workflow


class WorkerCrash(Exception):
    """Stands in for a worker dying in the middle of a node."""


def _start(thread_id: str) -> dict[str, Any]:
    return {
        "task_id": f"{thread_id}-task",
        "trace_id": f"{thread_id}-trace",
        "user_request": "Crie uma API segura para cadastro de clientes.",
        "status": "ANALYZING",
        "evidence": [],
    }


@pytest.fixture
def agent_calls(monkeypatch: pytest.MonkeyPatch) -> Counter[str]:
    """Count agent calls; the architecture agent crashes on its first call only."""
    calls: Counter[str] = Counter()
    real_requirements = RequirementsAgent.run
    real_architecture = ArchitectureAgent.run

    def requirements(self: RequirementsAgent, *args: Any, **kwargs: Any) -> Any:
        calls["requirements"] += 1
        return real_requirements(self, *args, **kwargs)

    def architecture(self: ArchitectureAgent, *args: Any, **kwargs: Any) -> Any:
        calls["architecture"] += 1
        if calls["architecture"] == 1:
            raise WorkerCrash
        return real_architecture(self, *args, **kwargs)

    monkeypatch.setattr(RequirementsAgent, "run", requirements)
    monkeypatch.setattr(ArchitectureAgent, "run", architecture)
    return calls


def test_recovery_resumes_after_the_last_completed_node(agent_calls: Counter[str]) -> None:
    graph = build_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "recover-mid-graph"}}

    with pytest.raises(WorkerCrash):
        invoke_workflow(graph, config, _start("recover-mid-graph"), recover=False)

    result = invoke_workflow(graph, config, _start("recover-mid-graph"), recover=True)

    assert result["status"] == "HUMAN_REVIEW"
    assert result["architecture"]
    # Requirements finished before the crash and is not executed again.
    assert agent_calls == Counter({"requirements": 1, "architecture": 2})


def test_recovery_reuses_state_of_a_thread_waiting_for_review(
    agent_calls: Counter[str],
) -> None:
    graph = build_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "recover-waiting"}}
    agent_calls["architecture"] = 1  # skip the simulated crash
    invoke_workflow(graph, config, _start("recover-waiting"), recover=False)
    calls_before = agent_calls.copy()

    result = invoke_workflow(graph, config, _start("recover-waiting"), recover=True)

    assert result["status"] == "HUMAN_REVIEW"
    assert agent_calls == calls_before


def test_recovery_without_checkpoint_starts_from_the_beginning(
    agent_calls: Counter[str],
) -> None:
    graph = build_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "recover-empty"}}
    agent_calls["architecture"] = 1  # skip the simulated crash

    result = invoke_workflow(graph, config, _start("recover-empty"), recover=True)

    assert result["status"] == "HUMAN_REVIEW"
    assert agent_calls["requirements"] == 1


def test_recovered_resume_applies_a_decision_that_never_reached_the_graph(
    agent_calls: Counter[str],
) -> None:
    graph = build_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "recover-resume"}}
    agent_calls["architecture"] = 1  # skip the simulated crash
    invoke_workflow(graph, config, _start("recover-resume"), recover=False)
    decision = Command(
        resume={
            "status": "APPROVED",
            "reviewer": "security-reviewer",
            "justification": "Risk accepted with compensating controls.",
            "decided_at": datetime.now(UTC).isoformat(),
        }
    )

    result = invoke_workflow(graph, config, decision, recover=True, resume_interrupt=True)

    assert result["status"] == "COMPLETED"
    assert result["human_review"]["status"] == "APPROVED"
