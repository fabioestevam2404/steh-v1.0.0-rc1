import re
from pathlib import Path

import yaml

from app.models.implementation import ToolExecutionResult

_SAFE_PATH = re.compile(r"^[A-Za-z0-9_./-]+$")


class CapabilityViolation(RuntimeError):
    pass


class ToolGateway:
    def __init__(self, policy_path: str = "policies/capabilities.yaml") -> None:
        self.policy = yaml.safe_load(
            Path(policy_path).read_text(encoding="utf-8")
        )
        self.root = Path(self.policy["capabilities"]["workspace"]["root"])

    def workspace_for(self, task_id: str) -> Path:
        safe_task = re.sub(r"[^A-Za-z0-9_-]", "_", task_id)
        workspace = (self.root / safe_task).resolve()
        root = self.root.resolve()
        if root not in workspace.parents and workspace != root:
            raise CapabilityViolation("Workspace path escape detected.")
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    def write_file(
        self,
        task_id: str,
        relative_path: str,
        content: str,
    ) -> ToolExecutionResult:
        cfg = self.policy["capabilities"]["workspace"]
        limits = self.policy["limits"]

        if not cfg["allow_create_files"]:
            raise CapabilityViolation("File creation is disabled.")

        if not _SAFE_PATH.fullmatch(relative_path):
            raise CapabilityViolation("Unsafe path characters.")

        if Path(relative_path).is_absolute() or ".." in Path(relative_path).parts:
            raise CapabilityViolation("Path escape is prohibited.")

        encoded = content.encode("utf-8")
        if len(encoded) > int(limits["max_file_bytes"]):
            raise CapabilityViolation("File exceeds configured size limit.")

        workspace = self.workspace_for(task_id)
        target = (workspace / relative_path).resolve()

        if workspace not in target.parents:
            raise CapabilityViolation("Target escaped workspace.")

        target.parent.mkdir(parents=True, exist_ok=True)
        existed = target.exists()
        target.write_text(content, encoding="utf-8")

        return ToolExecutionResult(
            tool="workspace.write_file",
            success=True,
            artifact=relative_path,
            message="modified" if existed else "created",
        )

    def delete_file(self, task_id: str, relative_path: str) -> None:
        raise CapabilityViolation("File deletion is prohibited in Alpha 0.4.")

    def run_shell(self, command: str) -> None:
        raise CapabilityViolation("Shell execution is prohibited in Alpha 0.4.")
