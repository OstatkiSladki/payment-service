from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session as core_get_db_session
from core.security import InternalAuthHeaders, get_internal_auth_headers
from schemas.auth import StaffRole, UsersRole


class CurrentUser(BaseModel):
  user_id: int
  role: UsersRole
  staff_role: StaffRole | None = None
  email: str
  is_active: bool
  is_verified: bool
  venue_id: int | None = None
  request_id: str


async def get_db_session() -> AsyncIterator[AsyncSession]:
  async for session in core_get_db_session():
    yield session


async def get_current_user(
  auth_headers: InternalAuthHeaders = Depends(get_internal_auth_headers),
) -> CurrentUser:
  if auth_headers.role == UsersRole.STAFF and auth_headers.staff_role is None:
    raise HTTPException(
      status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
      detail={
        "code": "VALIDATION_ERROR",
        "message": "X-User-Staff-Role header is required for staff users",
        "request_id": auth_headers.request_id,
      },
    )

  return CurrentUser(
    user_id=auth_headers.user_id,
    role=auth_headers.role,
    staff_role=auth_headers.staff_role,
    email=auth_headers.email,
    is_active=auth_headers.is_active,
    is_verified=auth_headers.is_verified,
    venue_id=auth_headers.venue_id,
    request_id=auth_headers.request_id,
  )
