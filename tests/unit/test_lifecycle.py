class FakeRun:
    status = "STARTED"


class FakeDB:
    pass


def test_lifecycle_wraps_actual_execution(
    monkeypatch,
):
    events = []

    import app.orchestration.lifecycle as module

    def start_agent_run(*args, **kwargs):
        events.append("STARTED")
        return FakeRun()

    def complete_agent_run(*args, **kwargs):
        events.append("SUCCEEDED")

    def fail_agent_run(*args, **kwargs):
        events.append("FAILED")

    monkeypatch.setattr(
        module,
        "start_agent_run",
        start_agent_run,
    )

    monkeypatch.setattr(
        module,
        "complete_agent_run",
        complete_agent_run,
    )

    monkeypatch.setattr(
        module,
        "fail_agent_run",
        fail_agent_run,
    )

    class Result:
        result = {}
        evidence = []
        confidence = 1.0

    lifecycle = module.AgentLifecycle(
        FakeDB(),
        "task",
        "trace",
    )

    def actual():
        events.append(
            "ACTUAL_EXECUTION"
        )
        return Result()

    lifecycle.execute(
        "agent",
        actual,
    )

    assert events == [
        "STARTED",
        "ACTUAL_EXECUTION",
        "SUCCEEDED",
    ]