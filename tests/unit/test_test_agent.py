from app.agents.test_engineer import TestAgent
from app.tools.gateway import ToolGateway
from app.tools.validator import ControlledValidator


def test_test_agent_passes_clean_artifact(tmp_path):
    gateway = ToolGateway()
    gateway.root = tmp_path
    gateway.write_file("task", "main.py", "x = 1\n")
    agent = TestAgent(ControlledValidator(gateway))
    result = agent.run("task", {"files_created": ["main.py"]})
    assert result.result["test_passed"] is True
    assert result.result["scanners_passed"] is True


def _agent(tmp_path) -> tuple[TestAgent, ToolGateway]:
    gateway = ToolGateway()
    gateway.root = tmp_path
    return TestAgent(ControlledValidator(gateway)), gateway


def _integrity(result) -> dict:
    return next(t for t in result.result["tests"] if t["name"] == "workspace_integrity")


def test_empty_workspace_fails_validation(tmp_path):
    # Regression: an empty workspace used to pass (syntax SKIPPED, no scan findings).
    agent, _ = _agent(tmp_path)
    result = agent.run("task", {"files_created": ["main.py"]})

    assert result.result["test_passed"] is False
    assert _integrity(result)["status"] == "FAIL"
    assert "main.py" in _integrity(result)["details"]


def test_implementation_without_declared_files_fails_validation(tmp_path):
    agent, gateway = _agent(tmp_path)
    gateway.write_file("task", "main.py", "x = 1\n")

    result = agent.run("task", {"files_created": [], "files_modified": []})

    assert result.result["test_passed"] is False
    assert _integrity(result)["details"].startswith("Implementation declared no files")


def test_missing_declared_file_fails_even_when_others_exist(tmp_path):
    agent, gateway = _agent(tmp_path)
    gateway.write_file("task", "app/main.py", "x = 1\n")

    result = agent.run(
        "task",
        {"files_created": ["app/main.py"], "files_modified": ["app/routes.py"]},
    )

    assert result.result["test_passed"] is False
    details = _integrity(result)["details"]
    assert "app/routes.py" in details
    assert "app/main.py" not in details


def test_created_and_modified_files_present_pass_integrity(tmp_path):
    agent, gateway = _agent(tmp_path)
    gateway.write_file("task", "app/main.py", "x = 1\n")
    gateway.write_file("task", "app/routes.py", "y = 2\n")

    result = agent.run(
        "task",
        {"files_created": ["app/main.py"], "files_modified": ["app/routes.py"]},
    )

    assert result.result["test_passed"] is True
    assert _integrity(result)["status"] == "PASS"
