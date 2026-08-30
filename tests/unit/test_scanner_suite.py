from app.tools.process_runner import ProcessResult
from app.tools.scanners import ScannerSuite

class FakeRunner:
    def run_scanner(self, scanner, workspace):
        if scanner == "semgrep":
            return ProcessResult(
                True, 0,
                '{"results":[{"check_id":"x","extra":{"severity":"ERROR"}}]}',
                "", 1.0
            )
        if scanner == "trivy":
            return ProcessResult(True,0,'{"Results":[]}',"",1.0)
        return ProcessResult(True,0,"","",1.0)

def test_scanners_are_normalized(tmp_path) -> None:
    evidence=ScannerSuite(FakeRunner()).run_all(tmp_path)
    assert len(evidence)==3
    assert evidence[0].scanner=="semgrep"
    assert evidence[0].findings
