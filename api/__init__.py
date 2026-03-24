from fastapi import APIRouter, Depends

from api import admin, health, payments, promo, webhooks
from dependency import get_current_user

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(
  payments.router,
  prefix="/payments",
  tags=["Payments"],
  dependencies=[Depends(get_current_user)],
)
api_router.include_router(
  promo.router,
  prefix="/promo",
  tags=["Promo Codes"],
  dependencies=[Depends(get_current_user)],
)
api_router.include_router(
  admin.router,
  prefix="/admin",
  tags=["Admin"],
  dependencies=[Depends(get_current_user)],
)
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
