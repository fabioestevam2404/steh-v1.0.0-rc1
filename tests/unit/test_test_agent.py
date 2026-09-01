from app.agents.test_engineer import TestAgent
from app.tools.gateway import ToolGateway
from app.tools.validator import ControlledValidator


def test_test_agent_passes_clean_artifact(tmp_path):
    gateway=ToolGateway()
    gateway.root=tmp_path
    gateway.write_file("task","main.py","x = 1\n")
    agent=TestAgent(ControlledValidator(gateway))
    result=agent.run("task",{})
    assert result.result["test_passed"] is True
    assert result.result["scanners_passed"] is True
