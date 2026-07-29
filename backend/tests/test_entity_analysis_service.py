from __future__ import annotations

from datetime import datetime

from app.services.entity_analysis_service import EntityAnalysisService


def test_first_appearance_and_usage_counting():
    """
    Test that EntityAnalysisService correctly identifies earliest appearance and counts usages.
    """
    service = EntityAnalysisService()

    t1 = datetime(2026, 1, 1, 10, 0, 0)
    t2 = datetime(2026, 1, 15, 14, 0, 0)
    t3 = datetime(2026, 2, 1, 9, 0, 0)

    occurrences = [
        {"entity_type": "Phone", "lookup_value": "+919876543210", "complaint_id": "c-2", "created_at": t2},
        {"entity_type": "Phone", "lookup_value": "+919876543210", "complaint_id": "c-1", "created_at": t1},
        {"entity_type": "Phone", "lookup_value": "+919876543210", "complaint_id": "c-3", "created_at": t3},
    ]

    result = service.analyze_entities(occurrences)

    assert len(result) == 1
    info = result[0]
    assert info.entity_type == "Phone"
    assert info.entity_value == "+919876543210"
    assert info.first_seen == t1
    assert info.first_seen_complaint == "c-1"
    assert info.usage_count == 3


def test_duplicate_handling_within_same_complaint():
    """
    Test that multiple occurrences within the same complaint count as 1 usage.
    """
    service = EntityAnalysisService()
    t1 = datetime(2026, 1, 10, 12, 0, 0)

    occurrences = [
        {"entity_type": "UPI", "lookup_value": "test@upi", "complaint_id": "c-100", "created_at": t1},
        {"entity_type": "UPI", "lookup_value": "test@upi", "complaint_id": "c-100", "created_at": t1},
    ]

    result = service.analyze_entities(occurrences)

    assert len(result) == 1
    assert result[0].usage_count == 1
    assert result[0].first_seen == t1
    assert result[0].first_seen_complaint == "c-100"


def test_chronological_ordering_of_multiple_entities():
    """
    Test that results are sorted by first_seen datetime ascending.
    """
    service = EntityAnalysisService()

    t_earliest = datetime(2026, 1, 1, 8, 0, 0)
    t_later = datetime(2026, 3, 1, 8, 0, 0)

    occurrences = [
        {"entity_type": "Email", "lookup_value": "later@domain.com", "complaint_id": "c-2", "created_at": t_later},
        {"entity_type": "Phone", "lookup_value": "+911111111111", "complaint_id": "c-1", "created_at": t_earliest},
    ]

    result = service.analyze_entities(occurrences)

    assert len(result) == 2
    assert result[0].entity_value == "+911111111111"
    assert result[0].first_seen == t_earliest
    assert result[1].entity_value == "later@domain.com"
    assert result[1].first_seen == t_later


def test_empty_occurrences():
    """
    Test that empty occurrences return an empty list.
    """
    service = EntityAnalysisService()
    assert service.analyze_entities([]) == []
