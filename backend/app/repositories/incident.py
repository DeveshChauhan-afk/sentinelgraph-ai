# app/repositories/incident.py

"""
Incident Repository.

Custom data access operations for Incident domain entity.
Includes support for pagination, complex search, and filtering.
"""

from typing import Optional
from sqlalchemy import select, desc, asc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.incident import Incident
from app.models.enums import IncidentStatus, Priority, ScamCategory
from app.repositories.base import BaseRepository


class IncidentRepository(BaseRepository[Incident]):
    """
    Repository for Incident operations, extending BaseRepository with domain-specific queries.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(Incident, session)

    async def get_by_status(
        self, status: IncidentStatus, skip: int = 0, limit: int = 100
    ) -> list[Incident]:
        """Fetch incidents filtered by status with pagination."""
        stmt = (
            select(Incident).where(Incident.status == status).offset(skip).limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_priority(
        self, priority: Priority, skip: int = 0, limit: int = 100
    ) -> list[Incident]:
        """Fetch incidents filtered by priority with pagination."""
        stmt = (
            select(Incident)
            .where(Incident.priority == priority)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_scam_category(
        self, category: ScamCategory, skip: int = 0, limit: int = 100
    ) -> list[Incident]:
        """Fetch incidents filtered by scam category with pagination."""
        stmt = (
            select(Incident)
            .where(Incident.scam_category == category)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_case_reference(self, case_reference: str) -> Optional[Incident]:
        """Fetch a specific incident by its external reference ID."""
        return await self.first(case_reference=case_reference)

    async def get_recent(self, limit: int = 10) -> list[Incident]:
        """Fetch the most recently created incidents."""
        stmt = select(Incident).order_by(desc(Incident.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_processing_queue(self, limit: int = 20) -> list[Incident]:
        """Fetch oldest 'new' or 'processing' incidents for triage."""
        stmt = (
            select(Incident)
            .where(Incident.status.in_([IncidentStatus.NEW, IncidentStatus.PROCESSING]))
            .order_by(asc(Incident.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_high_risk(
        self, threshold: float = 0.8, skip: int = 0, limit: int = 100
    ) -> list[Incident]:
        """Fetch high-risk incidents, excluding NULLs and supporting pagination."""
        stmt = (
            select(Incident)
            .where(Incident.risk_score.is_not(None), Incident.risk_score >= threshold)
            .order_by(desc(Incident.risk_score))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search(
        self, query: str, skip: int = 0, limit: int = 100
    ) -> list[Incident]:
        """Search incidents with relevance-based (newest first) ordering."""
        stmt = (
            select(Incident)
            .where(
                or_(
                    Incident.title.ilike(f"%{query}%"),
                    Incident.description.ilike(f"%{query}%"),
                )
            )
            .order_by(desc(Incident.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all(self) -> list[Incident]:
        """
        Retrieve all incidents ordered by creation time.
        """
        result = await self._session.execute(
            select(Incident).order_by(Incident.created_at)
        )
        return list(result.scalars().all())
