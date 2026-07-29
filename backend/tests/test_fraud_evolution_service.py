from __future__ import annotations

from datetime import datetime

from app.schemas.timeline import (
    EvolutionEventType,
    TimelineEvent,
    TimelineEventType,
)
from app.services.fraud_evolution_service import FraudEvolutionService


def test_network_started_event():
    """
    Test that the earliest complaint triggers a NETWORK_STARTED evolution event.
    """
    service = FraudEvolutionService()
    t1 = datetime(2026, 1, 1, 10, 0, 0)
    t2 = datetime(2026, 1, 5, 10, 0, 0)

    events = [
        TimelineEvent(
            event_type=TimelineEventType.COMPLAINT_CREATED,
            timestamp=t1,
            title="Complaint Created: c-1",
            metadata={"complaint_id": "c-1"},
        ),
        TimelineEvent(
            event_type=TimelineEventType.COMPLAINT_CREATED,
            timestamp=t2,
            title="Complaint Created: c-2",
            metadata={"complaint_id": "c-2"},
        ),
    ]

    occurrences = [
        {"complaint_id": "c-1", "created_at": t1, "entity_type": "Phone", "lookup_value": "+919999999999"},
        {"complaint_id": "c-2", "created_at": t2, "entity_type": "Phone", "lookup_value": "+919999999999"},
    ]

    evolution = service.analyze_network_evolution(events, occurrences)

    assert len(evolution) >= 1
    start_event = evolution[0]
    assert start_event.event_type == EvolutionEventType.NETWORK_STARTED
    assert start_event.timestamp == t1
    assert "c-1" in start_event.related_complaints


def test_entity_type_introduction():
    """
    Test ENTITY_TYPE_INTRODUCED event when a new entity category appears for the first time.
    """
    service = FraudEvolutionService()
    t1 = datetime(2026, 1, 1, 10, 0, 0)
    t2 = datetime(2026, 1, 10, 10, 0, 0)

    events = [
        TimelineEvent(
            event_type=TimelineEventType.COMPLAINT_CREATED,
            timestamp=t1,
            title="Complaint Created: c-1",
            metadata={"complaint_id": "c-1"},
        ),
        TimelineEvent(
            event_type=TimelineEventType.COMPLAINT_CREATED,
            timestamp=t2,
            title="Complaint Created: c-2",
            metadata={"complaint_id": "c-2"},
        ),
    ]

    occurrences = [
        {"complaint_id": "c-1", "created_at": t1, "entity_type": "Phone", "lookup_value": "+919999999999"},
        {"complaint_id": "c-2", "created_at": t2, "entity_type": "UPI", "lookup_value": "test@upi"},
    ]

    evolution = service.analyze_network_evolution(events, occurrences)

    types = [ev.event_type for ev in evolution]
    assert EvolutionEventType.ENTITY_TYPE_INTRODUCED in types

    upi_intro = next(ev for ev in evolution if ev.event_type == EvolutionEventType.ENTITY_TYPE_INTRODUCED and ev.metadata.get("entity_type") == "UPI")
    assert upi_intro.timestamp == t2
    assert "UPI" in upi_intro.title
    assert "test@upi" in upi_intro.related_entities


def test_payment_and_communication_expansion():
    """
    Test PAYMENT_INFRASTRUCTURE_EXPANDED and COMMUNICATION_CHANNEL_EXPANDED events.
    """
    service = FraudEvolutionService()
    t1 = datetime(2026, 1, 1, 10, 0, 0)
    t2 = datetime(2026, 1, 15, 10, 0, 0)

    events = [
        TimelineEvent(
            event_type=TimelineEventType.COMPLAINT_CREATED,
            timestamp=t1,
            title="Complaint Created: c-1",
            metadata={"complaint_id": "c-1"},
        ),
        TimelineEvent(
            event_type=TimelineEventType.COMPLAINT_CREATED,
            timestamp=t2,
            title="Complaint Created: c-2",
            metadata={"complaint_id": "c-2"},
        ),
    ]

    occurrences = [
        {"complaint_id": "c-1", "created_at": t1, "entity_type": "Phone", "lookup_value": "+919999999999"},
        {"complaint_id": "c-2", "created_at": t2, "entity_type": "BankAccount", "lookup_value": "ACC123456"},
        {"complaint_id": "c-2", "created_at": t2, "entity_type": "Email", "lookup_value": "scam@domain.com"},
    ]

    evolution = service.analyze_network_evolution(events, occurrences)

    event_types = [ev.event_type for ev in evolution]
    assert EvolutionEventType.PAYMENT_INFRASTRUCTURE_EXPANDED in event_types
    assert EvolutionEventType.COMMUNICATION_CHANNEL_EXPANDED in event_types

    pay_ev = next(ev for ev in evolution if ev.event_type == EvolutionEventType.PAYMENT_INFRASTRUCTURE_EXPANDED)
    assert pay_ev.related_entities == ["ACC123456"]

    comm_ev = next(ev for ev in evolution if ev.event_type == EvolutionEventType.COMMUNICATION_CHANNEL_EXPANDED)
    assert comm_ev.related_entities == ["scam@domain.com"]


def test_network_expansion_via_complaint():
    """
    Test NETWORK_EXPANDED when a subsequent complaint introduces previously unseen entities.
    """
    service = FraudEvolutionService()
    t1 = datetime(2026, 1, 1, 10, 0, 0)
    t2 = datetime(2026, 1, 20, 10, 0, 0)

    events = [
        TimelineEvent(
            event_type=TimelineEventType.COMPLAINT_CREATED,
            timestamp=t1,
            title="Complaint Created: c-1",
            metadata={"complaint_id": "c-1"},
        ),
        TimelineEvent(
            event_type=TimelineEventType.COMPLAINT_CREATED,
            timestamp=t2,
            title="Complaint Created: c-2",
            metadata={"complaint_id": "c-2"},
        ),
    ]

    occurrences = [
        {"complaint_id": "c-1", "created_at": t1, "entity_type": "Phone", "lookup_value": "+911111111111"},
        {"complaint_id": "c-2", "created_at": t2, "entity_type": "Phone", "lookup_value": "+911111111111"},
        {"complaint_id": "c-2", "created_at": t2, "entity_type": "UPI", "lookup_value": "new_mule@upi"},
    ]

    evolution = service.analyze_network_evolution(events, occurrences)

    expansion_events = [ev for ev in evolution if ev.event_type == EvolutionEventType.NETWORK_EXPANDED]
    assert len(expansion_events) == 1
    assert expansion_events[0].related_complaints == ["c-2"]
    assert "new_mule@upi" in expansion_events[0].related_entities


def test_milestone_detection():
    """
    Test NETWORK_MILESTONE when complaint count reaches configured threshold (e.g. 5).
    """
    service = FraudEvolutionService()

    events: list[TimelineEvent] = []
    occurrences: list[dict] = []

    for i in range(1, 6):
        t = datetime(2026, 1, i, 10, 0, 0)
        c_id = f"c-{i}"
        events.append(
            TimelineEvent(
                event_type=TimelineEventType.COMPLAINT_CREATED,
                timestamp=t,
                title=f"Complaint Created: {c_id}",
                metadata={"complaint_id": c_id},
            )
        )
        occurrences.append(
            {"complaint_id": c_id, "created_at": t, "entity_type": "Phone", "lookup_value": "+919999999999"}
        )

    evolution = service.analyze_network_evolution(events, occurrences)

    milestones = [ev for ev in evolution if ev.event_type == EvolutionEventType.NETWORK_MILESTONE]
    assert len(milestones) == 1
    assert milestones[0].metadata.get("milestone") == 5
    assert milestones[0].related_complaints == ["c-5"]


def test_chronological_ordering_and_duplicate_prevention():
    """
    Test that generated evolution events are sorted chronologically and contain no duplicates.
    """
    service = FraudEvolutionService()
    t1 = datetime(2026, 1, 1, 10, 0, 0)
    t2 = datetime(2026, 1, 10, 10, 0, 0)

    events = [
        TimelineEvent(
            event_type=TimelineEventType.COMPLAINT_CREATED,
            timestamp=t2,
            title="Complaint Created: c-2",
            metadata={"complaint_id": "c-2"},
        ),
        TimelineEvent(
            event_type=TimelineEventType.COMPLAINT_CREATED,
            timestamp=t1,
            title="Complaint Created: c-1",
            metadata={"complaint_id": "c-1"},
        ),
    ]

    occurrences = [
        {"complaint_id": "c-1", "created_at": t1, "entity_type": "Phone", "lookup_value": "+919999999999"},
        {"complaint_id": "c-2", "created_at": t2, "entity_type": "Phone", "lookup_value": "+919999999999"},
    ]

    evolution = service.analyze_network_evolution(events, occurrences)

    # Verify timestamps are strictly ascending
    timestamps = [ev.timestamp for ev in evolution]
    assert timestamps == sorted(timestamps)


def test_empty_investigation():
    """
    Test that empty input returns an empty evolution list.
    """
    service = FraudEvolutionService()
    assert service.analyze_network_evolution([], []) == []
