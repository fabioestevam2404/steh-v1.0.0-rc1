from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings
from app.db.session import get_db, get_engine, get_session_factory
from app.main import app


class _FakeSession:
    def __init__(self, fail: bool) -> None:
        self.fail = fail
        self.statements: list[str] = []

    def execute(self, statement: Any) -> None:
        self.statements.append(str(statement))
        if self.fail:
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))


@pytest.fixture
def fake_db() -> Iterator[Callable[[bool], _FakeSession]]:
    """Replace the database dependency with an in-memory fake."""

    def install(fail: bool) -> _FakeSession:
        session = _FakeSession(fail)
        app.dependency_overrides[get_db] = lambda: session
        return session

    yield install
    app.dependency_overrides.pop(get_db, None)


def test_readiness_uses_the_injected_session(
    fake_db: Callable[[bool], _FakeSession],
) -> None:
    session = fake_db(False)
    # No lifespan (no `with`), so no real database or checkpointer is touched.
    response = TestClient(app).get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}
    assert session.statements == ["SELECT 1"]


def test_readiness_reports_503_when_database_fails(
    fake_db: Callable[[bool], _FakeSession],
) -> None:
    fake_db(True)
    response = TestClient(app).get("/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database is not ready."}


def test_settings_and_engine_follow_environment_after_cache_reset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://steh:steh@db.example:6543/other")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    caches = (get_settings, get_engine, get_session_factory)
    for cached in caches:
        cached.cache_clear()
    try:
        assert get_settings().log_level == "DEBUG"
        engine = get_engine()
        assert engine.url.host == "db.example"
        assert engine.url.port == 6543
        assert get_session_factory().kw["bind"] is engine
    finally:
        for cached in caches:
            cached.cache_clear()
