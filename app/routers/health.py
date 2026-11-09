from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/health")
async def health() -> dict[str, str]:
    """Does NOT touch the database."""
    return {"status": "ok", "service": "api"}

@router.get("/health/db")
async def health_db(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    """Runs SELECT 1."""
    try:
        # text("SELECT 1") le dice a SQLAlchemy que ejecute SQL puro de forma segura
        await session.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        # If the database connection fails, we log the error and raise an HTTPException.
        raise HTTPException(
            status_code=503,
            detail="Database connection failed",
        )