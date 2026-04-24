from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from api import api_router
from core.config import get_settings
from core.database import close_engine
from services.grpc_clients import OrderServiceClient, VenueServiceClient

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
  order_service_client = OrderServiceClient()
  venue_service_client = VenueServiceClient()
  app.state.order_service_client = order_service_client
  app.state.venue_service_client = venue_service_client
  if settings.grpc_startup_checks_enabled:
    await order_service_client.wait_until_serving()
    await venue_service_client.wait_until_serving()
  try:
    yield
  finally:
    await order_service_client.close()
    await venue_service_client.close()
    await close_engine()


def create_app() -> FastAPI:
  app = FastAPI(
    title="Payment Service",
    version="1.0.0",
    debug=settings.app_debug,
    root_path=settings.app_root_path,
    lifespan=lifespan,
  )
  app.include_router(api_router)
  return app


app = create_app()

if __name__ == "__main__":
  uvicorn.run(
    app, host=settings.app_host, port=settings.app_port, log_level=settings.log_level.lower()
  )
