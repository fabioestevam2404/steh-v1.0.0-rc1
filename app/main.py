from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.tasks import router as tasks_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.orchestration.checkpoint import (
    close_checkpointer,
    init_checkpointer,
)
from app.version import __version__


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    init_checkpointer()
    yield
    close_checkpointer()


# Composition root: the ASGI app is built at import time, so this is the one
# place where configuration is read during import.
app = FastAPI(
    title=get_settings().app_name,
    version=__version__,
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(tasks_router)
app.include_router(metrics_router)
