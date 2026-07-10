"""
Application dependency providers.

Provides repositories and services for FastAPI dependency injection.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.repositories.incident import IncidentRepository
from app.services.incident_service import IncidentService


def get_incident_repository(
    session: AsyncSession = Depends(get_db),
) -> IncidentRepository:
    """
    Create an IncidentRepository for the current request.
    """
    return IncidentRepository(session)


def get_incident_service(
    repository: IncidentRepository = Depends(get_incident_repository),
) -> IncidentService:
    """
    Create an IncidentService for the current request.
    """
    return IncidentService(repository)
