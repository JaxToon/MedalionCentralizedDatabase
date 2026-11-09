from pydantic import BaseModel

from app.core.errors import ErrorCode


class ErrorDetail(BaseModel):
    code: ErrorCode
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
