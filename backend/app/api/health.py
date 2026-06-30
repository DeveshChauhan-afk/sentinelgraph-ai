# app/api/health.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get(
    "/",
    summary="Application health check",
    tags=["Health"],
)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Perform a liveness and readiness check.
    
    Verifies PostgreSQL connectivity. If database is unreachable,
    returns 503 Service Unavailable.
    """
    try:
        # Execute a simple query to verify connection
        await db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "service": settings.PROJECT_NAME
        }
    except Exception:
        # Log the full traceback for operational debugging
        logger.exception("Database health check failed.")
        
        # Raise 503 Service Unavailable for orchestrators (Kubernetes/Docker)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "database": "disconnected",
                "service": settings.PROJECT_NAME,
            },
        )