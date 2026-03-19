from fastapi import APIRouter, status

from schemas.common import HealthChecks, HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check() -> HealthResponse:
  # TODO: run actual DB ping and optional cache checks.
  return HealthResponse(
    status="healthy", version="1.2.0", checks=HealthChecks(database="ok", cache=None)
  )
