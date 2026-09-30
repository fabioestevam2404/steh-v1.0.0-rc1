from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.metrics import render
from app.db.session import get_db
from app.services.metrics import render_state_metrics

router = APIRouter(tags=["observability"])

DbSession = Annotated[Session, Depends(get_db)]

_DATABASE_UP = (
    "# HELP steh_metrics_database_up Whether task and queue metrics could be read.\n"
    "# TYPE steh_metrics_database_up gauge\n"
    "steh_metrics_database_up {value}\n"
)


@router.get("/metrics", response_class=PlainTextResponse)
def metrics(db: DbSession) -> str:
    payload = render()
    try:
        state = render_state_metrics(db)
    except SQLAlchemyError:
        # Keep serving process metrics so a database outage is itself observable.
        return payload + _DATABASE_UP.format(value=0)
    return payload + state + _DATABASE_UP.format(value=1)
