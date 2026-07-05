"""Health check endpoint."""

from fastapi import APIRouter
from sqlalchemy import text

from app.database import engine

router = APIRouter()


@router.get("/health")
async def health_check():
    """Liveness + DB connectivity probe.

    Uses the engine directly (not the get_db dependency) so a dead database
    yields a "degraded" JSON response instead of a 500 from session teardown.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "down"
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "service": "stock-analyze-api",
        "database": db_status,
    }
