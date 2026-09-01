from app.agents.implementation import ImplementationAgent
from app.tools.gateway import ToolGateway


def test_stub_implementation_writes_only_workspace(tmp_path) -> None:
    gateway = ToolGateway()
    gateway.root = tmp_path
    agent = ImplementationAgent("stub", "test", None, gateway=gateway)

    result = agent.run(
        "task-1",
        {"functional_requirements": ["API"]},
        {"components": []},
        {"threat_model": {"security_requirements": ["validate input"]}},
    )

    assert result.status == "SUCCESS"
    assert result.result["files_created"]
    assert (tmp_path / "task-1" / "generated_app" / "main.py").exists()
