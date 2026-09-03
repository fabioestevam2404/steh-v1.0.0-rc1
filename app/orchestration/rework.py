from pathlib import Path

import yaml

from app.models.scanning import ReworkDecision


class ReworkController:
    def __init__(self, policy_path: str = "policies/execution.yaml") -> None:
        self.policy = yaml.safe_load(
            Path(policy_path).read_text(encoding="utf-8")
        )

    @property
    def automatic(self) -> bool:
        return bool(self.policy["rework"].get("automatic", False))

    def decide(
        self,
        current_attempt: int,
        reasons: list[str],
    ) -> ReworkDecision:
        max_attempts = int(self.policy["rework"]["max_attempts"])
        if max_attempts < 1:
            raise ValueError("rework.max_attempts must be at least 1")

        required = bool(reasons)
        exhausted = required and current_attempt >= max_attempts

        return ReworkDecision(
            required=required,
            attempt=current_attempt,
            max_attempts=max_attempts,
            exhausted=exhausted,
            automatic=self.automatic,
            reasons=reasons,
        )
