"""FastAPI application: routes, request logging, and the structured error envelope."""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import health, users
from app.core.config import get_settings
from app.core.errors import AppError, ErrorCode
from app.core.logging import configure_logging, request_id_var
from app.schemas.errors import ErrorDetail, ErrorResponse

API_PREFIX = "/api/v1"
REQUEST_ID_HEADER = "X-Request-ID"

request_logger = logging.getLogger("app.request")

_HTTP_ERROR_CODES = {404: ErrorCode.NOT_FOUND, 405: ErrorCode.METHOD_NOT_ALLOWED}


def error_response(status_code: int, code: ErrorCode, message: str) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status_code, content=jsonable_encoder(body))


async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    return error_response(exc.status_code, exc.code, exc.message)


async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _HTTP_ERROR_CODES.get(exc.status_code, ErrorCode.HTTP_ERROR)
    response = error_response(exc.status_code, code, str(exc.detail))
    response.headers.update(exc.headers or {})
    return response


async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    fields = ", ".join(".".join(map(str, err["loc"])) for err in exc.errors())
    return error_response(422, ErrorCode.VALIDATION_ERROR, f"Invalid request: {fields}")


async def request_context(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Assign a request id, turn unhandled errors into a safe 500, and log the request."""
    request_id = uuid.uuid4().hex
    token = request_id_var.set(request_id)
    started = time.perf_counter()
    try:
        try:
            response = await call_next(request)
        except Exception:
            request_logger.exception("unhandled error")
            response = error_response(
                500, ErrorCode.INTERNAL_ERROR, "An unexpected error occurred."
            )
        response.headers[REQUEST_ID_HEADER] = request_id
        request_logger.info(
            "request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                "actor_id": getattr(request.state, "actor_id", None),
            },
        )
        return response
    finally:
        request_id_var.reset(token)


def create_app() -> FastAPI:
    configure_logging(get_settings().log_level)

    app = FastAPI(title="Banking Data Lakehouse Simulator API", version="0.1.0")
    app.middleware("http")(request_context)
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)

    app.include_router(health.router)
    app.include_router(users.router, prefix=API_PREFIX)
    return app


app = create_app()
