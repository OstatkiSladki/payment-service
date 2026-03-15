from fastapi import HTTPException

from schemas.common import ErrorResponse


class ServiceError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str, request_id: str | None = None) -> None:
        super().__init__(status_code=status_code, detail=ErrorResponse(code=code, message=message, request_id=request_id).model_dump())
