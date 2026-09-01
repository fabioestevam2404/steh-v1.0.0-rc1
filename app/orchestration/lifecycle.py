from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.contracts import AgentResult
from app.services.audit import (
    complete_agent_run,
    fail_agent_run,
    start_agent_run,
)


class AgentLifecycle:
    def __init__(
        self,
        db: Session,
        task_id: UUID,
        trace_id: UUID,
    ) -> None:
        self.db = db
        self.task_id = task_id
        self.trace_id = trace_id

    def execute(
        self,
        agent_name: str,
        fn: Callable[[], AgentResult],
    ) -> AgentResult:
        run = start_agent_run(
            self.db,
            self.task_id,
            self.trace_id,
            agent_name,
        )

        try:
            result = fn()

            complete_agent_run(
                self.db,
                run,
                result.result,
                result.evidence,
                result.confidence,
            )

            return result

        except Exception as exc:
            fail_agent_run(
                self.db,
                run,
                type(exc).__name__,
            )
            raise