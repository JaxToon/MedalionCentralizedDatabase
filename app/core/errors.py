"""The single error type the API turns into `{"error": {"code", "message"}}` responses."""

from enum import StrEnum


class ErrorCode(StrEnum):
    """Stable, client-facing error codes. Add codes; never rename them."""

    DEMO_USER_HEADER_MISSING = "DEMO_USER_HEADER_MISSING"
    DEMO_USER_UNKNOWN = "DEMO_USER_UNKNOWN"
    DEMO_USER_INACTIVE = "DEMO_USER_INACTIVE"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    HTTP_ERROR = "HTTP_ERROR"
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    def __init__(self, status_code: int, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
