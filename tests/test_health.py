import pytest
from httpx import ASGITransport, AsyncClient
from app.main import create_app  # Import the function that creates the FastAPI app instance
from app.core.config import Settings

def make_test_settings() -> Settings:
    # never used for a connection: /health does not touch the DB
    return Settings(database_url="postgresql+asyncpg://unused:unused@localhost/unused")

@pytest.mark.asyncio
async def test_health_endpoint():
  """Tests the health endpoint."""

  app = create_app(make_test_settings())  # Create the FastAPI app instance with test settings
  transport = ASGITransport(app=app)

  
  # We use a fictional 'base_url' because the request is resolved internally in memory
  async with AsyncClient(
      transport=transport, base_url="http://testserver"
  ) as client:

    # Performing the asynchronous request to the endpoint
    response = await client.get("/api/v1/health")

    # Asserting that the response meets the specifications
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api"}
