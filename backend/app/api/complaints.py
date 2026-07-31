# app/api/complaints.py
"""
Complaint API.

Public endpoints for reporting and viewing fraud complaints.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_incident_service
from app.schemas.incident import (
    IncidentCreate,
    IncidentResponse,
    IncidentListResponse,
)
from app.services.incident_service import IncidentService

router = APIRouter()


@router.post(
    "/",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report a new complaint",
)
async def create_complaint(
    complaint: IncidentCreate,
    service: IncidentService = Depends(get_incident_service),
) -> IncidentResponse:
    """
    Submit a new fraud complaint.
    """
    incident = await service.create_incident(complaint)
    return IncidentResponse.model_validate(incident)


@router.get(
    "/",
    response_model=list[IncidentListResponse],
    summary="List complaints",
)
async def list_complaints(
    skip: int = 0,
    limit: int = 100,
    service: IncidentService = Depends(get_incident_service),
) -> list[IncidentListResponse]:
    """
    Retrieve reported complaints.
    """
    incidents = await service.list_incidents(skip=skip, limit=limit)

    response = []

    for incident in incidents:
        dto = IncidentListResponse.model_validate(incident)
        dto.graph_node_id = f"complaint:{incident.id}"
        response.append(dto)

    return response


@router.get(
    "/{incident_id}",
    response_model=IncidentResponse,
    summary="Get complaint",
)
async def get_complaint(
    incident_id: UUID,
    service: IncidentService = Depends(get_incident_service),
) -> IncidentResponse:
    """
    Retrieve a complaint by its ID.
    """
    incident = await service.get_incident(incident_id)

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )

    return IncidentResponse.model_validate(incident)
