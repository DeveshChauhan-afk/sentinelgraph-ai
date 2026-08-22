# app/api/metrics.py

from fastapi import APIRouter, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter()


@router.get(
    "",
    summary="Prometheus metrics exposition",
    tags=["Metrics"],
)
def get_metrics() -> Response:
    """
    Exposes the default Prometheus registry metrics in standard Prometheus text format.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
        status_code=status.HTTP_200_OK,
    )
