from typing import Any

from langgraph.checkpoint.memory import MemorySaver

from app.agents.implementation import ImplementationAgent
from app.agents.security import SecurityAgent
from app.agents.test_engineer import TestAgent
from app.models.contracts import AgentResult
from app.orchestration.graph import build_graph


def agent_result(agent: str, result: dict[str, Any]) -> AgentResult:
    return AgentResult(
        agent=agent,
        status="SUCCESS",
        result=result,
        confidence=1.0,
    )


def run_rework_graph(
    monkeypatch: Any,
    validation_results: list[bool],
) -> tuple[dict[str, Any], dict[str, int]]:
    calls = {"implementation": 0, "validation": 0}

    def security_run(self: SecurityAgent, *args: Any) -> AgentResult:
        return agent_result(
            "security_agent",
            {
                "overall_risk": "LOW",
                "findings": [],
                "threat_model": {"security_requirements": ["validate input"]},
            },
        )

    def implementation_run(self: ImplementationAgent, *args: Any) -> AgentResult:
        calls["implementation"] += 1
        return agent_result(
            "implementation_agent",
            {"files_created": ["generated_app/main.py"]},
        )

    def validation_run(self: TestAgent, *args: Any) -> AgentResult:
        passed = validation_results[calls["validation"]]
        calls["validation"] += 1
        return agent_result(
            "test_agent",
            {"test_passed": passed, "scanners_passed": True},
        )

    monkeypatch.setattr(SecurityAgent, "run", security_run)
    monkeypatch.setattr(ImplementationAgent, "run", implementation_run)
    monkeypatch.setattr(TestAgent, "run", validation_run)

    result = build_graph(checkpointer=MemorySaver()).invoke(
        {
            "task_id": "rework-task",
            "trace_id": "rework-trace",
            "user_request": "Crie uma API segura para cadastro de clientes.",
            "status": "ANALYZING",
            "evidence": [],
        },
        config={"configurable": {"thread_id": "rework-test"}},
    )
    return result, calls


def test_failed_validation_reworks_then_completes(monkeypatch: Any) -> None:
    result, calls = run_rework_graph(monkeypatch, [False, True])

    assert result["status"] == "COMPLETED"
    assert result["rework_count"] == 1
    assert calls == {"implementation": 2, "validation": 2}
    assert len(result["rework_history"]) == 2
    assert result["rework_history"][0]["required"] is True
    assert result["rework_decision"]["required"] is False


def test_rework_stops_when_attempts_are_exhausted(monkeypatch: Any) -> None:
    result, calls = run_rework_graph(monkeypatch, [False, False])

    assert result["status"] == "REWORK_EXHAUSTED"
    assert result["rework_count"] == 2
    assert calls == {"implementation": 2, "validation": 2}
    assert result["rework_decision"]["exhausted"] is True
