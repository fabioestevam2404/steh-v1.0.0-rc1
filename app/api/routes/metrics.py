from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from app.core.metrics import render

router = APIRouter(tags=["observability"])

@router.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    return render()
