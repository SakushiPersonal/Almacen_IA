from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import get_settings
from app.routers import health
from app.db.session import engine


# 1. Configuración del ciclo de vida (Lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
  # El código aquí se ejecuta UNA SOLA VEZ cuando la API arranca
  settings = get_settings()
  print(f"Arrancando {settings.app_name} en entorno: {settings.environment}")

  yield

  # El código aquí se ejecuta UNA SOLA VEZ cuando la API se apaga
  print("Apagando la aplicación... Limpiando conexiones.")
  await engine.dispose()  # Cierra correctamente el pool de conexiones a la DB


# 2. Inicialización de FastAPI
settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

# 3. Registro de Routers
# Usamos un prefijo '/api/v1' para mantener las rutas ordenadas y profesionales
app.include_router(health.router, prefix="/api/v1", tags=["Health"])


# 4. Ruta raíz opcional para bienvenida o redirección
@app.get("/")
async def root():
  return {
      "message": f"Welcome to {settings.app_name}",
      "docs_url": "/docs",
  }