import pytest
from app.tools.gateway import CapabilityViolation, ToolGateway

def test_gateway_rejects_path_escape(tmp_path) -> None:
    gateway = ToolGateway()
    gateway.root = tmp_path
    with pytest.raises(CapabilityViolation):
        gateway.write_file("task", "../escape.py", "bad")

def test_gateway_rejects_shell() -> None:
    gateway = ToolGateway()
    with pytest.raises(CapabilityViolation):
        gateway.run_shell("echo unsafe")

def test_gateway_writes_inside_workspace(tmp_path) -> None:
    gateway = ToolGateway()
    gateway.root = tmp_path
    result = gateway.write_file("task", "src/main.py", "print('ok')")
    assert result.success
    assert (tmp_path / "task" / "src" / "main.py").exists()
