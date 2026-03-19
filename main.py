import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI

from api import api_router
from core.config import get_settings
from core.database import close_engine

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
  # TODO: add startup checks for DB/RabbitMQ connectivity when infra contracts are finalized.
  yield
  await close_engine()


def create_app() -> FastAPI:
  app = FastAPI(
    title="Payment Service",
    version="1.0.0",
    debug=settings.app_debug,
    lifespan=lifespan,
  )
  app.include_router(api_router)
  return app


app = create_app()

if __name__ == "__main__":
  uvicorn.run(
    app, host=settings.app_host, port=settings.app_port, log_level=settings.log_level.lower()
  )
