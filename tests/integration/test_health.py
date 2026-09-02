import pytest

from app.api.routes.health import health, ready


def test_health_reports_application_version() -> None:
    response = health()

    assert response["status"] == "ok"
    assert response["version"] == "1.0.0-rc2"


@pytest.mark.integration
def test_readiness_checks_database() -> None:
    assert ready() == {"status": "ready", "database": "ok"}
