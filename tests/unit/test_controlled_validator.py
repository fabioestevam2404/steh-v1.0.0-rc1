from app.tools.gateway import ToolGateway
from app.tools.validator import ControlledValidator


def validator(tmp_path):
    gateway=ToolGateway()
    gateway.root=tmp_path
    return gateway, ControlledValidator(gateway)

def test_valid_python_passes(tmp_path):
    gateway,v=validator(tmp_path)
    gateway.write_file("t","main.py","x = 1\n")
    tests=v.syntax_tests("t")
    assert tests[0].status == "PASS"

def test_invalid_python_fails(tmp_path):
    gateway,v=validator(tmp_path)
    gateway.write_file("t","main.py","def broken(:\n")
    tests=v.syntax_tests("t")
    assert tests[0].status == "FAIL"

def test_secret_is_critical(tmp_path):
    gateway,v=validator(tmp_path)
    gateway.write_file("t","config.py",'api_key = "super-secret-value"\n')
    findings=v.secret_scan("t")
    assert findings
    assert findings[0].severity == "CRITICAL"

def test_dangerous_exec_is_high(tmp_path):
    gateway,v=validator(tmp_path)
    gateway.write_file("t","main.py",'exec("print(1)")\n')
    findings=v.sast_scan("t")
    assert findings
    assert findings[0].severity == "HIGH"
