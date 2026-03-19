from collections.abc import AsyncIterator

from fastapi import Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db_session as core_get_db_session
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
  x_user_id: int = Header(alias="X-User-ID"),
  x_user_role: UsersRole = Header(alias="X-User-Role"),
  x_user_staff_role: StaffRole | None = Header(default=None, alias="X-User-Staff-Role"),
  x_user_email: str = Header(alias="X-User-Email"),
  x_user_is_active: bool = Header(alias="X-User-Is-Active"),
  x_user_is_verified: bool = Header(alias="X-User-Is-Verified"),
  x_user_venue_id: int | None = Header(default=None, alias="X-User-Venue-ID"),
  x_request_id: str = Header(alias="X-Request-ID"),
) -> CurrentUser:
  if x_user_role == UsersRole.STAFF and x_user_staff_role is None:
    raise HTTPException(
      status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
      detail={
        "code": "VALIDATION_ERROR",
        "message": "X-User-Staff-Role header is required for staff users",
        "request_id": x_request_id,
      },
    )

  return CurrentUser(
    user_id=x_user_id,
    role=x_user_role,
    staff_role=x_user_staff_role,
    email=x_user_email,
    is_active=x_user_is_active,
    is_verified=x_user_is_verified,
    venue_id=x_user_venue_id,
    request_id=x_request_id,
  )
