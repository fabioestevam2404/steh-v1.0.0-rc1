from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import SessionLocal
from app.version import __version__

router = APIRouter(tags=["health"])

@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}

@router.get("/ready")
def ready() -> dict[str, str]:
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}
