import pytest

from app.api.routes.health import health, ready
from app.db.session import new_session
from app.version import __version__


def test_health_reports_application_version() -> None:
    response = health()

    assert response["status"] == "ok"
    assert response["version"] == __version__


@pytest.mark.integration
def test_readiness_checks_database() -> None:
    with new_session() as db:
        assert ready(db) == {"status": "ready", "database": "ok"}
