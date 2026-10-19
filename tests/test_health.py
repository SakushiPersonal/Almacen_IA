import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app  # Importamos tu instancia de FastAPI configurada


@pytest.mark.asyncio
async def test_health_endpoint():
  """Prueba que el endpoint /health responda 200 OK usando AsyncClient y

  ASGITransport.
  """
  # 1. Configuramos el transporte ASGI con nuestra app de FastAPI
  transport = ASGITransport(app=app)

  # 2. Inicializamos el cliente asíncrono pasándole el transporte
  # Usamos un 'base_url' ficticio porque la petición se resuelve internamente en memoria
  async with AsyncClient(
      transport=transport, base_url="http://testserver"
  ) as client:

    # 3. Realizamos la petición asíncrona al endpoint (recuerda que añadimos el prefijo /api/v1)
    response = await client.get("/api/v1/health")

    # 4. Asertamos que la respuesta cumpla con las especificaciones
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "api"}
