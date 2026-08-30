from pathlib import Path
import yaml

from app.models.scanning import ReworkDecision


class ReworkController:
    def __init__(self, policy_path: str = "policies/execution.yaml") -> None:
        self.policy = yaml.safe_load(
            Path(policy_path).read_text(encoding="utf-8")
        )

    def decide(
        self,
        current_attempt: int,
        reasons: list[str],
    ) -> ReworkDecision:
        max_attempts = int(self.policy["rework"]["max_attempts"])
        required = bool(reasons)
        exhausted = required and current_attempt >= max_attempts

        return ReworkDecision(
            required=required,
            attempt=current_attempt,
            max_attempts=max_attempts,
            exhausted=exhausted,
            reasons=reasons,
        )
