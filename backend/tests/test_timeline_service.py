from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.graph.repository import GraphRepository
from app.schemas.timeline import TimelineEventType
from app.services.timeline_service import TimelineService


@pytest.mark.asyncio
async def test_single_complaint():
    """
    Test timeline construction with a single connected complaint.
    """
    mock_repo = AsyncMock(spec=GraphRepository)
    dt = datetime(2026, 1, 15, 10, 0, 0)
    mock_repo.get_connected_complaints.return_value = [
        {
            "complaint_id": "c-101",
            "lookup_value": "+919876543210",
            "created_at": dt,
        }
    ]

    service = TimelineService(repository=mock_repo)
    response = await service.build_timeline("+919876543210")

    assert response.investigation_target == "+919876543210"
    assert response.total_events == 1
    assert response.start_time == dt
    assert response.end_time == dt
    assert len(response.events) == 1
    assert response.events[0].event_type == TimelineEventType.COMPLAINT_CREATED
    assert response.events[0].timestamp == dt
    assert response.events[0].metadata["complaint_id"] == "c-101"


@pytest.mark.asyncio
async def test_multiple_complaints_chronological_ordering():
    """
    Test timeline construction with multiple complaints, ensuring chronological sorting.
    """
    mock_repo = AsyncMock(spec=GraphRepository)
    t1 = datetime(2026, 1, 10, 8, 0, 0)
    t2 = datetime(2026, 2, 20, 14, 30, 0)
    t3 = datetime(2026, 3, 5, 19, 15, 0)

    # Return unordered complaints from repository
    mock_repo.get_connected_complaints.return_value = [
        {"complaint_id": "c-3", "lookup_value": "user@example.com", "created_at": t3},
        {"complaint_id": "c-1", "lookup_value": "user@example.com", "created_at": t1},
        {"complaint_id": "c-2", "lookup_value": "user@example.com", "created_at": t2},
    ]

    service = TimelineService(repository=mock_repo)
    response = await service.build_timeline("user@example.com")

    assert response.investigation_target == "user@example.com"
    assert response.total_events == 3
    assert response.start_time == t1
    assert response.end_time == t3
    assert len(response.events) == 3

    # Check chronological ordering (ascending)
    assert response.events[0].metadata["complaint_id"] == "c-1"
    assert response.events[1].metadata["complaint_id"] == "c-2"
    assert response.events[2].metadata["complaint_id"] == "c-3"


@pytest.mark.asyncio
async def test_empty_timeline():
    """
    Test timeline construction when no connected complaints exist.
    """
    mock_repo = AsyncMock(spec=GraphRepository)
    mock_repo.get_connected_complaints.return_value = []

    service = TimelineService(repository=mock_repo)
    response = await service.build_timeline("empty-entity")

    assert response.investigation_target == "empty-entity"
    assert response.total_events == 0
    assert response.start_time is None
    assert response.end_time is None
    assert response.events == []


@pytest.mark.asyncio
async def test_missing_entity():
    """
    Test timeline reconstruction for an entity not found in the graph.
    """
    mock_repo = AsyncMock(spec=GraphRepository)
    mock_repo.get_connected_complaints.return_value = []

    service = TimelineService(repository=mock_repo)
    response = await service.build_timeline("non-existent-entity")

    assert response.investigation_target == "non-existent-entity"
    assert response.total_events == 0
    assert response.start_time is None
    assert response.end_time is None
    assert response.events == []


@pytest.mark.asyncio
async def test_duplicate_complaints():
    """
    Test deduplication when repository returns duplicate complaint entries.
    """
    mock_repo = AsyncMock(spec=GraphRepository)
    dt = datetime(2026, 1, 15, 10, 0, 0)
    mock_repo.get_connected_complaints.return_value = [
        {"complaint_id": "c-dup", "lookup_value": "upi@bank", "created_at": dt},
        {"complaint_id": "c-dup", "lookup_value": "upi@bank", "created_at": dt},
    ]

    service = TimelineService(repository=mock_repo)
    response = await service.build_timeline("upi@bank")

    assert response.total_events == 1
    assert len(response.events) == 1
    assert response.events[0].metadata["complaint_id"] == "c-dup"


@pytest.mark.asyncio
async def test_iso_string_timestamp_conversion():
    """
    Test automatic conversion of ISO string timestamps into datetime objects.
    """
    mock_repo = AsyncMock(spec=GraphRepository)
    mock_repo.get_connected_complaints.return_value = [
        {
            "complaint_id": "c-iso",
            "lookup_value": "target-iso",
            "created_at": "2026-04-12T16:45:00Z",
        }
    ]

    service = TimelineService(repository=mock_repo)
    response = await service.build_timeline("target-iso")

    assert response.total_events == 1
    assert isinstance(response.events[0].timestamp, datetime)
    assert response.events[0].timestamp.year == 2026
    assert response.events[0].timestamp.month == 4
    assert response.events[0].timestamp.day == 12


@pytest.mark.asyncio
async def test_end_to_end_orchestration():
    """
    Test full end-to-end orchestration including events, entity evolution, statistics, and insights.
    """
    mock_repo = AsyncMock(spec=GraphRepository)
    t1 = datetime(2026, 1, 1, 10, 0, 0)
    t2 = datetime(2026, 1, 15, 10, 0, 0)

    mock_repo.get_connected_complaints.return_value = [
        {"complaint_id": "c-1", "lookup_value": "+919999999999", "created_at": t1},
        {"complaint_id": "c-2", "lookup_value": "+919999999999", "created_at": t2},
    ]

    mock_repo.get_entity_occurrences.return_value = [
        {"entity_type": "Phone", "lookup_value": "+919999999999", "complaint_id": "c-1", "created_at": t1},
        {"entity_type": "Phone", "lookup_value": "+919999999999", "complaint_id": "c-2", "created_at": t2},
        {"entity_type": "UPI", "lookup_value": "fraud@upi", "complaint_id": "c-1", "created_at": t1},
        {"entity_type": "UPI", "lookup_value": "fraud2@upi", "complaint_id": "c-2", "created_at": t2},
    ]

    mock_repo.get_timeline_statistics.return_value = {
        "complaints": 2,
        "phones": 1,
        "upis": 2,
        "emails": 0,
        "urls": 0,
        "bank_accounts": 0,
        "organizations": 0,
        "people": 0,
        "locations": 0,
    }

    service = TimelineService(repository=mock_repo)
    response = await service.build_timeline("+919999999999")

    assert response.investigation_target == "+919999999999"
    assert response.total_events == 2
    assert response.start_time == t1
    assert response.end_time == t2

    # Verify entity_first_seen
    assert len(response.entity_first_seen) == 3


    # Verify statistics
    assert response.statistics is not None
    assert response.statistics.total_complaints == 2
    assert response.statistics.phones == 1
    assert response.statistics.upis == 2
    assert response.statistics.total_entities == 3

    # Verify insights
    assert len(response.insights) >= 1

    # Verify fraud evolution
    assert len(response.fraud_evolution) >= 1

    # Verify evidence
    assert len(response.evidence) >= 1



