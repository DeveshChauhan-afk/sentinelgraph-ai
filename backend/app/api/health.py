# app/api/health.py

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.health_service import HealthService

router = APIRouter()


@router.get(
    "/live",
    summary="Process liveness probe",
    status_code=status.HTTP_200_OK,
    tags=["Health"],
)
async def liveness_check() -> dict:
    """
    Process liveness check. Always returns 200 OK while app is running.
    Does not touch databases or external services.
    """
    return HealthService.check_liveness()


@router.get(
    "/ready",
    summary="Application readiness probe",
    tags=["Health"],
)
async def readiness_check(
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Readiness probe for database & service dependency health.
    Returns 200 OK when ready, 503 Service Unavailable when unready.
    """
    result = await HealthService.check_readiness(db)
    if not result["is_ready"]:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unready",
            "dependencies": result["details"],
        }

    return {
        "status": "ready",
        "dependencies": result["details"],
    }


@router.get(
    "",
    summary="Operational health summary",
    tags=["Health"],
    include_in_schema=True,
)
@router.get(
    "/",
    summary="Operational health summary",
    tags=["Health"],
    include_in_schema=False,
)
async def health_summary(
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Provides structured operational health summary of application and dependencies.
    Returns 200 OK if healthy, 503 if unhealthy.
    """
    summary = await HealthService.get_health_summary(db)
    if summary["status"] != "healthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return summary
