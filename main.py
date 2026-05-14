import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from api import api_router
from core.config import get_settings
from core.database import close_engine
from services.grpc_clients import OrderServiceClient, VenueServiceClient

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
  order_service_client = OrderServiceClient()
  venue_service_client = VenueServiceClient()
  app.state.order_service_client = order_service_client
  app.state.venue_service_client = venue_service_client
  if settings.grpc_startup_checks_enabled:
    results = await asyncio.gather(
      order_service_client.wait_until_serving(),
      venue_service_client.wait_until_serving(),
      return_exceptions=True,
    )
    for dep_name, result in zip(("order-service", "venue-service"), results):
      if isinstance(result, Exception):
        logger.warning(
          "gRPC startup health check failed for %s: %s; continuing with lazy reconnect",
          dep_name,
          result,
        )
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
