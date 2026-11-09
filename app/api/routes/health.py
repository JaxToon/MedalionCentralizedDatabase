import logging

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import SessionDep
from app.core.errors import AppError, ErrorCode
from app.schemas.errors import ErrorResponse
from app.schemas.health import HealthOut

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", responses={503: {"model": ErrorResponse}})
def health(session: SessionDep) -> HealthOut:
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("database health check failed", exc_info=True)
        raise AppError(503, ErrorCode.DATABASE_UNAVAILABLE, "The database is not reachable.")
    return HealthOut(status="ok", database="ok")
