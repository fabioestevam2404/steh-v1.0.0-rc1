from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response

from app.api.routes.health import router as health_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.tasks import router as tasks_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.metrics import inc_request
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


@app.middleware("http")
async def count_requests(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    response = await call_next(request)
    # Label by route template (e.g. /api/v1/tasks/{task_id}), never the raw path,
    # so task ids cannot explode metric cardinality.
    route = request.scope.get("route")
    path = getattr(route, "path", "unmatched")
    inc_request(request.method, path, response.status_code)
    return response


app.include_router(health_router)
app.include_router(tasks_router)
app.include_router(metrics_router)
