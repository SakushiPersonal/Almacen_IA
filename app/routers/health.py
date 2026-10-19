from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session

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
    except Exception as e:
        # Si la base de datos está caída, la petición fallará aquí
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {str(e)}",
        ) from e