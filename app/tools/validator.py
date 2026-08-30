import ast
import re
from pathlib import Path

from app.models.validation import ScanFinding, TestEvidence, ValidationStatus
from app.tools.gateway import ToolGateway


_SECRET_PATTERNS = [
    ("SECRET-001", re.compile(r"(?i)(api[_-]?key|password|secret)\s*=\s*['\"][^'\"]+['\"]")),
    ("SECRET-002", re.compile(r"sk-[A-Za-z0-9]{16,}")),
]

_DANGEROUS_PATTERNS = [
    ("SAST-001", re.compile(r"\beval\s*\("), "Use of eval()"),
    ("SAST-002", re.compile(r"\bexec\s*\("), "Use of exec()"),
    ("SAST-003", re.compile(r"\bos\.system\s*\("), "Use of os.system()"),
    ("SAST-004", re.compile(r"\bsubprocess\."), "Use of subprocess"),
]


class ControlledValidator:
    def __init__(self, gateway: ToolGateway | None = None) -> None:
        self.gateway = gateway or ToolGateway()

    def _files(self, task_id: str) -> list[Path]:
        workspace = self.gateway.workspace_for(task_id)
        return [p for p in workspace.rglob("*") if p.is_file()]

    def syntax_tests(self, task_id: str) -> list[TestEvidence]:
        evidence = []
        for path in self._files(task_id):
            if path.suffix != ".py":
                continue
            rel = str(path.relative_to(self.gateway.workspace_for(task_id)))
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=rel)
                evidence.append(TestEvidence(
                    name=f"python_syntax:{rel}",
                    status=ValidationStatus.PASS,
                    details="Python AST parse succeeded.",
                    artifact=rel,
                ))
            except SyntaxError as exc:
                evidence.append(TestEvidence(
                    name=f"python_syntax:{rel}",
                    status=ValidationStatus.FAIL,
                    details=f"Syntax error: {exc.msg} line {exc.lineno}",
                    artifact=rel,
                ))
        if not evidence:
            evidence.append(TestEvidence(
                name="python_syntax",
                status=ValidationStatus.SKIPPED,
                details="No Python files found.",
            ))
        return evidence

    def secret_scan(self, task_id: str) -> list[ScanFinding]:
        findings = []
        workspace = self.gateway.workspace_for(task_id)
        for path in self._files(task_id):
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            rel = str(path.relative_to(workspace))
            for rule_id, pattern in _SECRET_PATTERNS:
                if pattern.search(text):
                    findings.append(ScanFinding(
                        scanner="secret_scan",
                        rule_id=rule_id,
                        severity="CRITICAL",
                        path=rel,
                        message="Potential hard-coded secret detected.",
                    ))
        return findings

    def sast_scan(self, task_id: str) -> list[ScanFinding]:
        findings = []
        workspace = self.gateway.workspace_for(task_id)
        for path in self._files(task_id):
            if path.suffix != ".py":
                continue
            text = path.read_text(encoding="utf-8")
            rel = str(path.relative_to(workspace))
            for rule_id, pattern, message in _DANGEROUS_PATTERNS:
                if pattern.search(text):
                    findings.append(ScanFinding(
                        scanner="builtin_sast",
                        rule_id=rule_id,
                        severity="HIGH",
                        path=rel,
                        message=message,
                    ))
        return findings
