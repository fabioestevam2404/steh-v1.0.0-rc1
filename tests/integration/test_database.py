import pytest
from sqlalchemy import text

from app.db.session import engine


@pytest.mark.integration
def test_postgres_connection() -> None:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar_one()

    assert result == 1


@pytest.mark.integration
def test_pull_request_review_columns_are_migrated() -> None:
    with engine.connect() as conn:
        columns = set(
            conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'tasks' "
                    "AND column_name IN "
                    "('source_pull_request', 'pull_request_review')"
                )
            ).scalars()
        )

    assert columns == {"source_pull_request", "pull_request_review"}
