import pytest

from app.api.routes.health import health, ready
from app.db.session import new_session


def test_health_reports_application_version() -> None:
    response = health()

    assert response["status"] == "ok"
    assert response["version"] == "1.0.0-rc2"


@pytest.mark.integration
def test_readiness_checks_database() -> None:
    with new_session() as db:
        assert ready(db) == {"status": "ready", "database": "ok"}
