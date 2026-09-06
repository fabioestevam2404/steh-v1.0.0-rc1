from datetime import UTC, datetime

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.agents.llm_judge import LLMJudgeAgent
from app.core.config import settings
from app.orchestration.graph import build_graph


def _run_approved_workflow(thread_id: str) -> dict[str, object]:
    graph = build_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": thread_id}}
    graph.invoke(
        {
            "task_id": f"{thread_id}-task",
            "trace_id": f"{thread_id}-trace",
            "user_request": "Crie uma API segura para cadastro de clientes.",
            "status": "ANALYZING",
            "evidence": [],
        },
        config=config,
    )
    return graph.invoke(
        Command(
            resume={
                "status": "APPROVED",
                "reviewer": "security-reviewer",
                "justification": "Risk accepted with compensating controls.",
                "decided_at": datetime.now(UTC).isoformat(),
            }
        ),
        config=config,
    )


def test_patch_4a_nodes_precede_implementation() -> None:
    graph = build_graph(checkpointer=MemorySaver()).get_graph()

    assert "specification" in graph.nodes
    assert "specification_gate" in graph.nodes
    assert "test_planning" in graph.nodes
    assert "test_plan_gate" in graph.nodes


def test_context_snapshot_precedes_requirements() -> None:
    graph = build_graph(checkpointer=MemorySaver()).get_graph()

    assert "context" in graph.nodes
    assert any(
        edge.source == "context" and edge.target == "requirements"
        for edge in graph.edges
    )


def test_validation_gate_can_return_to_implementation() -> None:
    graph = build_graph(checkpointer=MemorySaver()).get_graph()

    assert any(
        edge.source == "validation_gate" and edge.target == "implementation"
        for edge in graph.edges
    )


def test_judge_runs_only_after_successful_validation_gate() -> None:
    graph = build_graph(checkpointer=MemorySaver()).get_graph()

    assert "judge" in graph.nodes
    assert any(
        edge.source == "validation_gate" and edge.target == "judge"
        for edge in graph.edges
    )
    assert any(edge.source == "judge" and edge.target == "__end__" for edge in graph.edges)


def test_high_security_risk_prevents_implementation() -> None:
    graph = build_graph(checkpointer=MemorySaver())
    result = graph.invoke(
        {
            "task_id": "test-task-alpha04",
            "trace_id": "test-trace",
            "user_request": "Crie uma API segura para gerenciamento de clientes.",
            "status": "ANALYZING",
            "evidence": [],
        },
        config={"configurable": {"thread_id": "alpha04-unit"}},
    )
    assert result["security_review"]
    assert result["specification"]
    assert result["status"] == "HUMAN_REVIEW"
    assert result["human_review"]["status"] == "PENDING"
    assert "test_plan" not in result
    assert "implementation" not in result


def test_rejected_human_review_blocks_from_checkpoint() -> None:
    graph = build_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "hitl-reject"}}
    graph.invoke(
        {
            "task_id": "hitl-task",
            "trace_id": "hitl-trace",
            "user_request": "Crie uma API segura para cadastro de clientes.",
            "status": "ANALYZING",
            "evidence": [],
        },
        config=config,
    )

    result = graph.invoke(
        Command(
            resume={
                "status": "REJECTED",
                "reviewer": "security-reviewer",
                "justification": "Residual risk was not accepted.",
                "decided_at": datetime.now(UTC).isoformat(),
            }
        ),
        config=config,
    )

    assert result["status"] == "BLOCKED"
    assert result["human_review"]["status"] == "REJECTED"
    assert result["human_review"]["reviewer"] == "security-reviewer"


def test_approved_human_review_resumes_to_completion() -> None:
    graph = build_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "hitl-approve"}}
    graph.invoke(
        {
            "task_id": "hitl-approved-task",
            "trace_id": "hitl-approved-trace",
            "user_request": "Crie uma API segura para cadastro de clientes.",
            "status": "ANALYZING",
            "evidence": [],
        },
        config=config,
    )

    result = graph.invoke(
        Command(
            resume={
                "status": "APPROVED",
                "reviewer": "security-reviewer",
                "justification": "Risk accepted with compensating controls.",
                "decided_at": datetime.now(UTC).isoformat(),
            }
        ),
        config=config,
    )

    assert result["status"] == "COMPLETED"
    assert result["human_review"]["status"] == "APPROVED"
    assert result["test_plan"]
    assert result["implementation"]
    assert result["validation"]
    assert result["judge_evaluation"]["status"] == "COMPLETED"
    assert result["judge_evaluation"]["authoritative"] is False


def test_disabled_judge_does_not_change_completed_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "judge_enabled", False)

    result = _run_approved_workflow("judge-disabled")

    assert result["status"] == "COMPLETED"
    judge = result["judge_evaluation"]
    assert isinstance(judge, dict)
    assert judge["status"] == "SKIPPED"
    assert judge["authoritative"] is False


def test_unavailable_judge_does_not_change_completed_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable(*_: object) -> object:
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(LLMJudgeAgent, "run", unavailable)

    result = _run_approved_workflow("judge-unavailable")

    assert result["status"] == "COMPLETED"
    judge = result["judge_evaluation"]
    assert isinstance(judge, dict)
    assert judge["status"] == "UNAVAILABLE"
    assert judge["error_type"] == "RuntimeError"
    assert judge["authoritative"] is False
