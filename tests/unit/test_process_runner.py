import pytest
from app.tools.process_runner import ContainerProcessRunner, RunnerError

def test_non_allowlisted_scanner_is_rejected(tmp_path) -> None:
    runner=ContainerProcessRunner()
    with pytest.raises(RunnerError):
        runner.run_scanner("bash", tmp_path)
