from __future__ import annotations

from datetime import datetime

from app.schemas.timeline import (
    EntityTimelineInfo,
    InsightSeverity,
    TimelineEvent,
    TimelineEventType,
)
from app.services.timeline_analysis_service import TimelineAnalysisService


def test_statistics_generation():
    """
    Test statistics calculation and total_entities computation.
    """
    service = TimelineAnalysisService()
    raw_stats = {
        "complaints": 5,
        "phones": 2,
        "upis": 3,
        "emails": 1,
        "urls": 0,
        "bank_accounts": 1,
        "organizations": 1,
        "people": 2,
        "locations": 1,
    }

    stats = service.compute_statistics(raw_stats)

    assert stats.total_complaints == 5
    assert stats.phones == 2
    assert stats.upis == 3
    assert stats.emails == 1
    assert stats.bank_accounts == 1
    assert stats.total_entities == 11  # 2+3+1+0+1+1+2+1 = 11


def test_reused_entity_insight_generation():
    """
    Test deterministic insight generation for reused entities (usage_count >= 3).
    """
    service = TimelineAnalysisService()
    t1 = datetime(2026, 1, 1, 10, 0, 0)

    entity_info = [
        EntityTimelineInfo(
            entity_type="Phone",
            entity_value="+919876543210",
            first_seen=t1,
            first_seen_complaint="c-1",
            usage_count=6,
        )
    ]
    raw_stats = {"complaints": 6, "phones": 1, "upis": 0, "emails": 0, "urls": 0, "bank_accounts": 0, "organizations": 0, "people": 0, "locations": 0}
    stats = service.compute_statistics(raw_stats)

    insights = service.compute_insights(events=[], entity_info=entity_info, statistics=stats)

    assert len(insights) >= 1
    reuse_insight = next(i for i in insights if i.title == "Entity Reuse Detected")
    assert "Phone number reused across 6 complaints." in reuse_insight.description
    assert reuse_insight.severity == InsightSeverity.HIGH


def test_investigation_duration_insight():
    """
    Test deterministic insight generation when investigation spans multiple days.
    """
    service = TimelineAnalysisService()
    t_start = datetime(2026, 1, 1, 10, 0, 0)
    t_end = datetime(2026, 1, 13, 10, 0, 0)

    events = [
        TimelineEvent(
            event_type=TimelineEventType.COMPLAINT_CREATED,
            timestamp=t_start,
            title="Start Complaint",
        ),
        TimelineEvent(
            event_type=TimelineEventType.COMPLAINT_CREATED,
            timestamp=t_end,
            title="End Complaint",
        ),
    ]
    stats = service.compute_statistics({})

    insights = service.compute_insights(events=events, entity_info=[], statistics=stats)

    assert len(insights) >= 1
    duration_insight = next(i for i in insights if i.title == "Extended Activity Duration")
    assert "Fraud activity persisted over 12 days." in duration_insight.description


def test_multiple_phones_and_upis_insights():
    """
    Test deterministic insights when multiple phones and UPIs are present.
    """
    service = TimelineAnalysisService()
    raw_stats = {
        "complaints": 3,
        "phones": 3,
        "upis": 2,
        "emails": 0,
        "urls": 0,
        "bank_accounts": 0,
        "organizations": 0,
        "people": 0,
        "locations": 0,
    }
    stats = service.compute_statistics(raw_stats)

    insights = service.compute_insights(events=[], entity_info=[], statistics=stats)

    titles = [i.title for i in insights]
    assert "Multiple Phone Numbers Detected" in titles
    assert "Multiple Payment Identifiers" in titles

    phone_insight = next(i for i in insights if i.title == "Multiple Phone Numbers Detected")
    assert phone_insight.description == "Multiple phone numbers participated in the investigation."

    upi_insight = next(i for i in insights if i.title == "Multiple Payment Identifiers")
    assert upi_insight.description == "Multiple payment identifiers detected."
