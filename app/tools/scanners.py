import json
from pathlib import Path

from app.models.scanning import ScannerEvidence
from app.tools.process_runner import ContainerProcessRunner


class ScannerSuite:
    def __init__(
        self,
        runner: ContainerProcessRunner | None = None,
    ) -> None:
        self.runner = runner or ContainerProcessRunner()

    def _normalize(self, scanner: str, result) -> ScannerEvidence:
        findings: list[dict] = []
        error = None

        if result.stdout.strip():
            try:
                payload = json.loads(result.stdout)
                if scanner == "semgrep":
                    findings = payload.get("results", [])
                elif scanner == "trivy":
                    for target in payload.get("Results", []) or []:
                        for vuln in target.get("Vulnerabilities", []) or []:
                            findings.append({
                                "severity": vuln.get("Severity", "UNKNOWN"),
                                "rule_id": vuln.get("VulnerabilityID", "TRIVY"),
                                "path": target.get("Target", ""),
                                "message": vuln.get("Title") or vuln.get("Description", ""),
                            })
                        for secret in target.get("Secrets", []) or []:
                            findings.append({
                                "severity": secret.get("Severity", "HIGH"),
                                "rule_id": secret.get("RuleID", "TRIVY-SECRET"),
                                "path": target.get("Target", ""),
                                "message": secret.get("Title", "Secret detected"),
                            })
            except json.JSONDecodeError:
                error = "Scanner returned malformed JSON."

        # Gitleaks writes report to container /tmp in this alpha image contract.
        # A non-zero result is preserved as evidence even if no JSON is available.
        if not result.success and not error:
            error = result.stderr[-2000:] or f"{scanner} returned non-zero exit code."

        return ScannerEvidence(
            scanner=scanner,
            success=result.success and error is None,
            exit_code=result.exit_code,
            duration_ms=result.duration_ms,
            findings=findings,
            error=error,
        )

    def run_all(self, workspace: Path) -> list[ScannerEvidence]:
        evidence = []
        for scanner in ("semgrep", "gitleaks", "trivy"):
            result = self.runner.run_scanner(scanner, workspace)
            evidence.append(self._normalize(scanner, result))
        return evidence
