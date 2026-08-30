from app.orchestration.graph import build_graph

def test_high_security_risk_prevents_implementation() -> None:
    graph = build_graph()
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
    assert result["status"] == "HUMAN_REVIEW"
    assert "implementation" not in result
