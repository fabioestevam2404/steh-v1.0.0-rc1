from langgraph.checkpoint.memory import MemorySaver

from app.orchestration.graph import build_graph


def test_patch_4a_nodes_precede_implementation() -> None:
    graph = build_graph(checkpointer=MemorySaver()).get_graph()

    assert "specification" in graph.nodes
    assert "specification_gate" in graph.nodes
    assert "test_planning" in graph.nodes
    assert "test_plan_gate" in graph.nodes


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
    assert "test_plan" not in result
    assert "implementation" not in result
