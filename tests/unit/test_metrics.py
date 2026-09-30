from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.metrics import inc_request, render
from app.db.session import get_db
from app.main import app


def test_metrics_render_operational_counters() -> None:
    inc_request("GET", "/health", 200)

    payload = render()

    assert "steh_http_requests_total" in payload
    assert 'method="GET",path="/health",status="200"' in payload


class _UnavailableDatabase:
    def execute(self, *_: Any) -> None:
        raise OperationalError("SELECT", {}, Exception("connection refused"))

    def get(self, *_: Any) -> None:
        return None


@pytest.fixture
def unavailable_db() -> Iterator[None]:
    app.dependency_overrides[get_db] = _UnavailableDatabase
    yield
    app.dependency_overrides.pop(get_db, None)


def test_requests_are_counted_by_route_template(unavailable_db: None) -> None:
    client = TestClient(app)
    task_id = uuid4()

    assert client.get("/health").status_code == 200
    assert client.get(f"/api/v1/tasks/{task_id}").status_code == 404

    payload = render()
    assert 'method="GET",path="/health",status="200"' in payload
    assert 'path="/api/v1/tasks/{task_id}",status="404"' in payload
    assert str(task_id) not in payload


def test_metrics_endpoint_survives_database_outage(unavailable_db: None) -> None:
    response = TestClient(app).get("/metrics")

    assert response.status_code == 200
    assert "steh_http_requests_total" in response.text
    assert "steh_metrics_database_up 0" in response.text
    assert "steh_task_jobs" not in response.text
    assert "steh_workflows_total" not in response.text
