import hashlib
import hmac

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from core.config import get_settings
from schemas.auth import StaffRole, UsersRole


x_user_id_header = APIKeyHeader(name="X-User-ID", scheme_name="X-User-ID", auto_error=False)
x_user_role_header = APIKeyHeader(name="X-User-Role", scheme_name="X-User-Role", auto_error=False)
x_user_staff_role_header = APIKeyHeader(
  name="X-User-Staff-Role",
  scheme_name="X-User-Staff-Role",
  auto_error=False,
)
x_user_email_header = APIKeyHeader(name="X-User-Email", scheme_name="X-User-Email", auto_error=False)
x_user_is_active_header = APIKeyHeader(
  name="X-User-Is-Active",
  scheme_name="X-User-Is-Active",
  auto_error=False,
)
x_user_is_verified_header = APIKeyHeader(
  name="X-User-Is-Verified",
  scheme_name="X-User-Is-Verified",
  auto_error=False,
)
x_user_venue_id_header = APIKeyHeader(
  name="X-User-Venue-ID",
  scheme_name="X-User-Venue-ID",
  auto_error=False,
)
x_request_id_header = APIKeyHeader(name="X-Request-ID", scheme_name="X-Request-ID", auto_error=False)


class InternalAuthHeaders(BaseModel):
  user_id: int
  role: UsersRole
  staff_role: StaffRole | None = None
  email: str
  is_active: bool
  is_verified: bool
  venue_id: int | None = None
  request_id: str


class WebhookSignatureVerifier:
  def __init__(self, secret_key: str | None = None) -> None:
    settings = get_settings()
    self.secret_key = (secret_key or settings.webhook_secret_key).encode()

  def verify(self, payload: bytes, signature: str | None) -> None:
    if not signature:
      raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing webhook signature"
      )

    expected_signature = hmac.new(self.secret_key, payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_signature, signature):
      raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature"
      )


def _parse_bool_header(name: str, value: str | None, request_id: str) -> bool:
  if value is None:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail={"code": "VALIDATION_ERROR", "message": f"{name} header is required", "request_id": request_id},
    )
  value_lower = value.lower()
  if value_lower in {"true", "1"}:
    return True
  if value_lower in {"false", "0"}:
    return False
  raise HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"code": "VALIDATION_ERROR", "message": f"{name} header must be boolean", "request_id": request_id},
  )


def _require_header(name: str, value: str | None, request_id: str) -> str:
  if value is None:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail={"code": "VALIDATION_ERROR", "message": f"{name} header is required", "request_id": request_id},
    )
  return value


def _parse_int_header(name: str, value: str, request_id: str) -> int:
  try:
    return int(value)
  except ValueError as exc:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail={"code": "VALIDATION_ERROR", "message": f"{name} header must be integer", "request_id": request_id},
    ) from exc


def get_internal_auth_headers(
  x_user_id: str | None = Security(x_user_id_header),
  x_user_role: str | None = Security(x_user_role_header),
  x_user_staff_role: str | None = Security(x_user_staff_role_header),
  x_user_email: str | None = Security(x_user_email_header),
  x_user_is_active: str | None = Security(x_user_is_active_header),
  x_user_is_verified: str | None = Security(x_user_is_verified_header),
  x_user_venue_id: str | None = Security(x_user_venue_id_header),
  x_request_id: str | None = Security(x_request_id_header),
) -> InternalAuthHeaders:
  request_id = x_request_id or "unknown-request"
  required_user_id = _require_header("X-User-ID", x_user_id, request_id)
  required_user_role = _require_header("X-User-Role", x_user_role, request_id)
  required_user_email = _require_header("X-User-Email", x_user_email, request_id)
  required_request_id = _require_header("X-Request-ID", x_request_id, request_id)

  try:
    parsed_role = UsersRole(required_user_role)
  except ValueError as exc:
    raise HTTPException(
      status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
      detail={"code": "VALIDATION_ERROR", "message": "X-User-Role header has invalid value", "request_id": required_request_id},
    ) from exc

  parsed_staff_role: StaffRole | None = None
  if x_user_staff_role is not None:
    try:
      parsed_staff_role = StaffRole(x_user_staff_role)
    except ValueError as exc:
      raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
          "code": "VALIDATION_ERROR",
          "message": "X-User-Staff-Role header has invalid value",
          "request_id": required_request_id,
        },
      ) from exc

  parsed_venue_id: int | None = None
  if x_user_venue_id is not None:
    parsed_venue_id = _parse_int_header("X-User-Venue-ID", x_user_venue_id, required_request_id)

  return InternalAuthHeaders(
    user_id=_parse_int_header("X-User-ID", required_user_id, required_request_id),
    role=parsed_role,
    staff_role=parsed_staff_role,
    email=required_user_email,
    is_active=_parse_bool_header("X-User-Is-Active", x_user_is_active, required_request_id),
    is_verified=_parse_bool_header("X-User-Is-Verified", x_user_is_verified, required_request_id),
    venue_id=parsed_venue_id,
    request_id=required_request_id,
  )
