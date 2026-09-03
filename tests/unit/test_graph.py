from datetime import UTC, datetime

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from app.orchestration.graph import build_graph


def test_patch_4a_nodes_precede_implementation() -> None:
    graph = build_graph(checkpointer=MemorySaver()).get_graph()

    assert "specification" in graph.nodes
    assert "specification_gate" in graph.nodes
    assert "test_planning" in graph.nodes
    assert "test_plan_gate" in graph.nodes


def test_validation_gate_can_return_to_implementation() -> None:
    graph = build_graph(checkpointer=MemorySaver()).get_graph()

    assert any(
        edge.source == "validation_gate" and edge.target == "implementation"
        for edge in graph.edges
    )


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
