from fastapi import APIRouter

from api import admin, health, payments, promo, webhooks

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments"])
api_router.include_router(promo.router, prefix="/promo", tags=["Promo Codes"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
