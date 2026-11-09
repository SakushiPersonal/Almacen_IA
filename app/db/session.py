from collections.abc import AsyncIterator
from functools import lru_cache
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import get_settings

# SQLAlchemy's Engine to administrate the database connection. This engine is an object that represents the database and allows executing SQL queries.
def build_engine(url:str) -> AsyncEngine:
    """Crea un engine de SQLAlchemy para la base de datos."""
    return create_async_engine(
        url,
        echo=False, # Switch to True if you want to see the SQL queries being executed in development.
    )

@lru_cache
def get_engine() -> AsyncEngine:
    """Devuelve el engine de SQLAlchemy para la base de datos."""
    return build_engine(get_settings().database_url)

#We create a sessionmaker that will be used to create sessions for interacting with the database.
@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Returns a sessionmaker for creating database sessions."""
    return async_sessionmaker(
        bind=get_engine(),
        expire_on_commit=False,
    )

async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per request, always closed."""
    factory = get_sessionmaker() # Easier to read than get_sessionmaker()()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()