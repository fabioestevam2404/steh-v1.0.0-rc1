import logging
import time
from collections.abc import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import log_context
from app.models.contracts import AgentResult
from app.services.audit import (
    complete_agent_run,
    fail_agent_run,
    start_agent_run,
)

logger = logging.getLogger("steh.agents")


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


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
        with log_context(task_id=self.task_id, trace_id=self.trace_id):
            run = start_agent_run(
                self.db,
                self.task_id,
                self.trace_id,
                agent_name,
            )
            started = time.perf_counter()
            logger.info(
                "agent_started",
                extra={"event": "agent_started", "agent": agent_name},
            )

            try:
                result = fn()

                complete_agent_run(
                    self.db,
                    run,
                    result.result,
                    result.findings,
                    result.evidence,
                    result.confidence,
                )
                logger.info(
                    "agent_completed",
                    extra={
                        "event": "agent_completed",
                        "agent": agent_name,
                        "status": "SUCCEEDED",
                        "duration_ms": _elapsed_ms(started),
                    },
                )

                return result

            except Exception as exc:
                fail_agent_run(
                    self.db,
                    run,
                    type(exc).__name__,
                )
                logger.error(
                    "agent_failed",
                    extra={
                        "event": "agent_failed",
                        "agent": agent_name,
                        "status": "FAILED",
                        "error_type": type(exc).__name__,
                        "duration_ms": _elapsed_ms(started),
                    },
                )
                raise
