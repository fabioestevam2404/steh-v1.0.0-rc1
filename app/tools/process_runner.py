import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ProcessResult:
    success: bool
    exit_code: int | None
    stdout: str
    stderr: str
    duration_ms: float


class RunnerError(RuntimeError):
    pass


class ContainerProcessRunner:
    ALLOWED_SCANNERS = {
        "semgrep",
        "gitleaks",
        "trivy",
    }

    def __init__(
        self,
        policy_path: str = "policies/execution.yaml",
    ) -> None:
        self.policy = yaml.safe_load(
            Path(policy_path).read_text(
                encoding="utf-8"
            )
        )

    @staticmethod
    def _to_text(value: bytes | str | None) -> str:
        if value is None:
            return ""

        if isinstance(value, bytes):
            return value.decode(
                "utf-8",
                errors="replace",
            )

        return value

    def run_scanner(
        self,
        scanner: str,
        workspace: Path,
    ) -> ProcessResult:
        if scanner not in self.ALLOWED_SCANNERS:
            raise RunnerError(
                "Scanner is not allowlisted."
            )

        cfg = self.policy["runner"]
        workspace = workspace.resolve()

        scanner_args = {
            "semgrep": [
                "semgrep",
                "scan",
                "--config",
                "auto",
                "--json",
                "/workspace",
            ],
            "gitleaks": [
                "gitleaks",
                "detect",
                "--source",
                "/workspace",
                "--report-format",
                "json",
                "--report-path",
                "/tmp/gitleaks.json",
                "--no-git",
            ],
            "trivy": [
                "trivy",
                "fs",
                "--format",
                "json",
                "--scanners",
                "vuln,secret,misconfig",
                "/workspace",
            ],
        }[scanner]

        command = [
            "docker",
            "run",
            "--rm",
            "--network",
            str(cfg["network"]),
            "--read-only",
            "--memory",
            f'{int(cfg["memory_mb"])}m',
            "--cpus",
            str(cfg["cpus"]),
            "--pids-limit",
            str(cfg["pids_limit"]),
            "--mount",
            (
                f"type=bind,src={workspace},"
                "dst=/workspace,readonly"
            ),
            str(cfg["image"]),
            *scanner_args,
        ]

        started = time.perf_counter()

        try:
            completed = subprocess.run(
                command,
                shell=False,
                capture_output=True,
                text=True,
                timeout=int(
                    cfg["timeout_seconds"]
                ),
                check=False,
            )

        except subprocess.TimeoutExpired as exc:
            stdout = self._to_text(exc.stdout)
            stderr = self._to_text(exc.stderr)

            if not stderr:
                stderr = "scanner timeout"

            return ProcessResult(
                success=False,
                exit_code=None,
                stdout=stdout,
                stderr=stderr,
                duration_ms=(
                    time.perf_counter()
                    - started
                )
                * 1000,
            )

        return ProcessResult(
            success=completed.returncode == 0,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_ms=(
                time.perf_counter()
                - started
            )
            * 1000,
        )