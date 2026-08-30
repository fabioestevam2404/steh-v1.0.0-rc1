import pytest

from app.orchestration.checkpoint import (
    close_checkpointer,
    init_checkpointer,
)


@pytest.mark.integration
def test_postgres_checkpointer_initializes() -> None:
    checkpointer = init_checkpointer()

    assert checkpointer is not None

    close_checkpointer()
