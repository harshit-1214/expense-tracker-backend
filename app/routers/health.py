"""Health check endpoint for uptime monitors and load balancers."""

import logging

from fastapi import APIRouter, HTTPException, status

from app.database.session import check_database_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Check that the API and database are running")
def health_check() -> dict[str, str]:
    try:
        check_database_connection()
    except Exception:
        logger.exception("Health check failed: database is unreachable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        )
    return {"status": "ok", "database": "connected"}
