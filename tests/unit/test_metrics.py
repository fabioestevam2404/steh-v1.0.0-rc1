from app.core.metrics import inc_request, inc_workflow, render


def test_metrics_render_operational_counters() -> None:
    inc_request("GET", "/health", 200)
    inc_workflow("COMPLETED")

    payload = render()

    assert "steh_http_requests_total" in payload
    assert 'method="GET",path="/health",status="200"' in payload
    assert 'steh_workflows_total{status="COMPLETED"}' in payload
