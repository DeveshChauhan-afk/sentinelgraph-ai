# app/api/health.py

from fastapi import APIRouter, Depends, Response, status

from app.core.config import settings
from app.core.health.models import (
    HealthSummaryResponse,
    LivenessResponse,
    ReadinessResponse,
)
from app.core.health.service import HealthService

router = APIRouter()


def get_health_service() -> HealthService:
    """
    FastAPI dependency provider for HealthService.
    """
    return HealthService()


@router.get(
    "/live",
    summary="Process liveness probe",
    response_model=LivenessResponse,
    status_code=status.HTTP_200_OK,
    tags=["Health"],
)
async def liveness_check() -> LivenessResponse:
    """
    Process liveness probe. Always returns HTTP 200 while event loop is responsive.
    Does not touch databases or external dependencies.
    """
    return LivenessResponse()


@router.get(
    "/ready",
    summary="Application readiness probe",
    response_model=ReadinessResponse,
    tags=["Health"],
)
async def readiness_check(
    response: Response,
    service: HealthService = Depends(get_health_service),
) -> ReadinessResponse:
    """
    Readiness probe for traffic routing.
    Returns HTTP 200 when ready (including DEGRADED state), HTTP 503 when unready.
    """
    deps = await service.check_dependencies()
    overall_status = service.determine_status(deps)
    is_ready = service.determine_readiness(deps)

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status=overall_status,
        is_ready=is_ready,
        dependencies=deps,
    )


@router.get(
    "",
    summary="Operational health summary",
    response_model=HealthSummaryResponse,
    tags=["Health"],
)
async def health_summary(
    service: HealthService = Depends(get_health_service),
) -> HealthSummaryResponse:
    """
    Detailed operational diagnostic summary.
    Always returns HTTP 200 with structured diagnostic document even if degraded or unhealthy.
    """
    deps = await service.check_dependencies()
    overall_status = service.determine_status(deps)

    return HealthSummaryResponse(
        status=overall_status,
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment="development" if settings.DEBUG else "production",
        dependencies=deps,
    )
