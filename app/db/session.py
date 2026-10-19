from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import get_settings

# 1. Se obtiene la configuración de la base de datos desde el archivo config.py
settings = get_settings()


# El engine de SQLAlchemy para manejar la conexión a la base de datos (Python a PostgreSQL)
engine = create_async_engine(
    settings.database_url,
    future=True,
    echo=False,  # Cambiar a True si necesitas ver los logs de SQL en desarrollo
)
#Se crea un sessionmaker para manejar las sesiones de la base de datos
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 3. La dependencia para tus endpoints de FastAPI
# Esta función se puede usar como una dependencia en tus rutas de FastAPI para obtener una sesión de base de datos por solicitud.
async def get_session() -> AsyncIterator[AsyncSession]:
  """FastAPI dependency: one session per request, always closed."""
  async with SessionLocal() as session:
    try:
      yield session
    finally:
      await session.close()