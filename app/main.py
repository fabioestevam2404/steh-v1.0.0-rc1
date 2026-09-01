from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.tasks import router as tasks_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.orchestration.checkpoint import (
    close_checkpointer,
    init_checkpointer,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging(settings.log_level)
    init_checkpointer()
    yield
    close_checkpointer()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0-rc1",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(tasks_router)
app.include_router(metrics_router)