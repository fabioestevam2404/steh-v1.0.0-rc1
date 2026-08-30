import pytest
from sqlalchemy import text

from app.db.session import engine


@pytest.mark.integration
def test_postgres_connection() -> None:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar_one()

    assert result == 1
