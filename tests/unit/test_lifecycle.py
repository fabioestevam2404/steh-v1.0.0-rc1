class FakeRun:
    status="STARTED"

class FakeDB:
    pass

def test_lifecycle_wraps_actual_execution(monkeypatch):
    events=[]
    import app.orchestration.lifecycle as module

    monkeypatch.setattr(module,"start_agent_run",lambda *a,**k:(events.append("STARTED") or FakeRun()))
    monkeypatch.setattr(module,"complete_agent_run",lambda *a,**k:events.append("SUCCEEDED"))
    monkeypatch.setattr(module,"fail_agent_run",lambda *a,**k:events.append("FAILED"))

    class Result:
        result={}
        evidence=[]
        confidence=1.0

    lifecycle=module.AgentLifecycle(FakeDB(),"task","trace")
    def actual():
        events.append("ACTUAL_EXECUTION")
        return Result()

    lifecycle.execute("agent",actual)
    assert events == ["STARTED","ACTUAL_EXECUTION","SUCCEEDED"]
