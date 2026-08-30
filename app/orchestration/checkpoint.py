from langgraph.checkpoint.postgres import PostgresSaver

from app.core.config import settings

_checkpointer_cm = None
_checkpointer = None


def init_checkpointer() -> PostgresSaver:
    global _checkpointer_cm, _checkpointer

    if _checkpointer is not None:
        return _checkpointer

    _checkpointer_cm = PostgresSaver.from_conn_string(
        settings.langgraph_database_url
    )
    _checkpointer = _checkpointer_cm.__enter__()
    _checkpointer.setup()

    return _checkpointer


def get_checkpointer() -> PostgresSaver:
    if _checkpointer is None:
        return init_checkpointer()
    return _checkpointer


def close_checkpointer() -> None:
    global _checkpointer_cm, _checkpointer

    if _checkpointer_cm is not None:
        _checkpointer_cm.__exit__(None, None, None)

    _checkpointer_cm = None
    _checkpointer = None
