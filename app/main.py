from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import Settings, get_settings
from app.routers import health
from app.db.session import get_engine
import logging

logger = logging.getLogger(__name__) 

# Initializing the FastAPI application instance.
def create_app(settings: Settings | None = None) -> FastAPI:
    """Creates and configures the FastAPI application instance."""
    if settings is None:
        settings = get_settings()

    # life cycle config (Lifespan)
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Code here runs ONCE when the API starts
        logger.info("Starting %s", settings.app_name)
        
        yield

        # Code here runs ONCE when the API shuts down
        logger.info("Shutting down %s", settings.app_name)
        await get_engine().dispose()  # close Correctly connection pool to DB

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    app= FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
    )

    # 3. Include routers
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])


    @app.get("/")
    async def root():
        """Optional root route for welcome message or redirection."""
        return {
            "message": f"Welcome to {settings.app_name}",
            "docs_url": "/docs",
        }
    return app

