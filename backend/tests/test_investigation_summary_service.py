"""
Unit tests for InvestigationSummaryService Architecture (Sprint 9 Phase 1.5 Refinements).

Validates canonical InvestigationSummary immutability, facts vs presentation separation,
typed findings with provenance, recommendation triggers, evidence aggregate metrics,
investigation data quality metrics, and async orchestration.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.schemas.investigation_summary import (
    FindingType,
    InvestigationDataQuality,
    InvestigationEntitySummary,
    InvestigationEvidenceSummary,
    InvestigationEvolutionSummary,
    InvestigationFinding,
    InvestigationMetadata,
    InvestigationOverview,
    InvestigationPresentation,
    InvestigationRecommendation,
    InvestigationStatistics,
    InvestigationSummary,
    InvestigationTimelineSummary,
)
from app.schemas.timeline import (
    EntityTimelineInfo,
    EvidenceSeverity,
    EvidenceType,
    EvolutionEventType,
    FraudEvolutionEvent,
    InsightSeverity,
    InvestigationEvidence,
    TimelineEvent,
    TimelineEventType,
    TimelineInsight,
    TimelineResponse,
    TimelineStatistics,
)
from app.services.investigation_summary_service import InvestigationSummaryService
from app.services.timeline_service import TimelineService


@pytest.fixture
def representative_inputs():
    """
    Fixture providing representative deterministic analysis outputs.
    """
    t1 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 5, 12, 0, 0, tzinfo=timezone.utc)

    events = [
        TimelineEvent(
            event_type=TimelineEventType.COMPLAINT_CREATED,
            timestamp=t1,
            title="Complaint Created: C-101",
            description="Complaint C-101 registered with target +919876543210",
            metadata={"complaint_id": "C-101"},
        ),
        TimelineEvent(
            event_type=TimelineEventType.COMPLAINT_CREATED,
            timestamp=t2,
            title="Complaint Created: C-102",
            description="Complaint C-102 registered with target +919876543210",
            metadata={"complaint_id": "C-102"},
        ),
    ]

    entity_info = [
        EntityTimelineInfo(
            entity_type="Phone",
            entity_value="+919876543210",
            first_seen=t1,
            first_seen_complaint="C-101",
            usage_count=5,
            complaint_ids=["C-101", "C-102"],
        ),
        EntityTimelineInfo(
            entity_type="UPI",
            entity_value="scammer@upi",
            first_seen=t1,
            first_seen_complaint="C-101",
            usage_count=3,
            complaint_ids=["C-101", "C-102"],
        ),
    ]

    statistics = TimelineStatistics(
        total_complaints=2,
        total_entities=2,
        phones=1,
        upis=1,
        emails=0,
        urls=0,
        bank_accounts=0,
        organizations=0,
        people=0,
        locations=0,
    )

    insights = [
        TimelineInsight(
            title="Entity Reuse Detected",
            description="Phone number reused across 5 complaints.",
            severity=InsightSeverity.HIGH,
        )
    ]

    fraud_evolution = [
        FraudEvolutionEvent(
            event_type=EvolutionEventType.NETWORK_STARTED,
            timestamp=t1,
            title="Fraud Network Started",
            description="Investigation begins with complaint C-101.",
            related_complaints=["C-101"],
        ),
        FraudEvolutionEvent(
            event_type=EvolutionEventType.PAYMENT_INFRASTRUCTURE_EXPANDED,
            timestamp=t2,
            title="Payment Infrastructure Expanded",
            description="Payment infrastructure expanded with scammer@upi.",
            related_entities=["scammer@upi"],
            related_complaints=["C-102"],
        ),
    ]

    evidence = [
        InvestigationEvidence(
            evidence_type=EvidenceType.ENTITY_REUSE,
            severity=EvidenceSeverity.HIGH,
            confidence=0.85,
            title="High Entity Reuse: Phone '+919876543210'",
            description="Phone '+919876543210' reused across 5 complaints.",
            supporting_entities=["+919876543210"],
            supporting_complaints=["C-101", "C-102"],
        ),
        InvestigationEvidence(
            evidence_type=EvidenceType.PAYMENT_EXPANSION,
            severity=EvidenceSeverity.HIGH,
            confidence=0.80,
            title="Payment Infrastructure Expansion",
            description="Payment infrastructure expanded with scammer@upi.",
            supporting_entities=["scammer@upi"],
            supporting_complaints=["C-102"],
        ),
    ]

    return {
        "events": events,
        "entity_info": entity_info,
        "statistics": statistics,
        "insights": insights,
        "fraud_evolution": fraud_evolution,
        "evidence": evidence,
    }


def test_canonical_summary_construction(representative_inputs):
    """
    Test summary construction from representative outputs and verify schema integrity.
    """
    service = InvestigationSummaryService()

    summary = service.create_summary_from_outputs(
        target_value="+919876543210",
        target_type="phone",
        events=representative_inputs["events"],
        entity_info=representative_inputs["entity_info"],
        statistics=representative_inputs["statistics"],
        insights=representative_inputs["insights"],
        fraud_evolution=representative_inputs["fraud_evolution"],
        evidence=representative_inputs["evidence"],
    )

    # 1. Check top-level type
    assert isinstance(summary, InvestigationSummary)

    # 2. Metadata
    assert isinstance(summary.metadata, InvestigationMetadata)
    assert summary.metadata.target_value == "+919876543210"
    assert summary.metadata.target_type == "phone"
    assert summary.metadata.summary_version == "1.0"
    assert summary.metadata.generated_by == "InvestigationSummaryService"

    # 3. Overview (Facts only)
    assert isinstance(summary.overview, InvestigationOverview)
    assert summary.overview.target_value == "+919876543210"
    assert summary.overview.total_complaints == 2
    assert summary.overview.total_entities == 2
    assert summary.overview.overall_risk_level == "HIGH"

    # 4. Presentation
    assert isinstance(summary.presentation, InvestigationPresentation)
    assert "Deterministic investigation summary" in summary.presentation.executive_summary
    assert "HIGH" in summary.presentation.risk_justification
    assert len(summary.presentation.key_takeaways) > 0

    # 5. Statistics
    assert isinstance(summary.statistics, InvestigationStatistics)
    assert summary.statistics.total_complaints == 2
    assert summary.statistics.phones == 1
    assert summary.statistics.upis == 1
    assert summary.statistics.entity_type_counts["phones"] == 1

    # 6. Timeline Summary
    assert isinstance(summary.timeline, InvestigationTimelineSummary)
    assert summary.timeline.total_events == 2
    assert summary.timeline.duration_days == 4
    assert len(summary.timeline.events) == 2

    # 7. Entity Summary
    assert isinstance(summary.entities, InvestigationEntitySummary)
    assert summary.entities.total_entities == 2
    assert summary.entities.reused_entities_count == 2
    assert len(summary.entities.entities) == 2

    # 8. Evolution Summary
    assert isinstance(summary.evolution, InvestigationEvolutionSummary)
    assert summary.evolution.total_evolution_events == 2
    assert len(summary.evolution.events) == 2

    # 9. Evidence Summary & Aggregate Metrics
    assert isinstance(summary.evidence, InvestigationEvidenceSummary)
    assert summary.evidence.total_evidence_units == 2
    assert summary.evidence.high_count == 2
    assert summary.evidence.highest_confidence == 0.85
    assert summary.evidence.average_confidence == round((0.85 + 0.80) / 2, 2)
    assert summary.evidence.highest_severity == "HIGH"
    assert len(summary.evidence.evidence_items) == 2

    # 10. Data Quality Metrics
    assert isinstance(summary.data_quality, InvestigationDataQuality)
    assert summary.data_quality.overall_data_quality == "HIGH"

    # 11. Typed Findings
    assert len(summary.findings) > 0
    assert all(isinstance(f, InvestigationFinding) for f in summary.findings)
    assert any(f.type == FindingType.ENTITY_REUSE for f in summary.findings)
    assert any(f.type == FindingType.PAYMENT_EXPANSION for f in summary.findings)

    # 12. Recommendations with Provenance
    assert len(summary.recommendations) > 0
    assert all(isinstance(r, InvestigationRecommendation) for r in summary.recommendations)
    rec = summary.recommendations[0]
    assert rec.trigger in ("PAYMENT_EXPANSION", "ENTITY_REUSE_THRESHOLD")
    assert len(rec.target_entities) > 0


def test_immutability(representative_inputs):
    """
    Test that InvestigationSummary and canonical sub-models are immutable (frozen).
    """
    service = InvestigationSummaryService()
    summary = service.create_summary_from_outputs(
        target_value="+919876543210",
        events=representative_inputs["events"],
    )

    with pytest.raises((ValidationError, AttributeError, TypeError)):
        summary.metadata = InvestigationMetadata(target_value="hack")

    with pytest.raises((ValidationError, AttributeError, TypeError)):
        summary.overview.total_complaints = 999


def test_no_information_loss(representative_inputs):
    """
    Verify no information is lost between source analysis outputs and the canonical InvestigationSummary.
    """
    service = InvestigationSummaryService()

    summary = service.create_summary_from_outputs(
        target_value="+919876543210",
        events=representative_inputs["events"],
        entity_info=representative_inputs["entity_info"],
        statistics=representative_inputs["statistics"],
        insights=representative_inputs["insights"],
        fraud_evolution=representative_inputs["fraud_evolution"],
        evidence=representative_inputs["evidence"],
    )

    # Check all events preserved
    assert list(summary.timeline.events) == representative_inputs["events"]

    # Check all entity info preserved
    assert list(summary.entities.entities) == representative_inputs["entity_info"]

    # Check all fraud evolution events preserved
    assert list(summary.evolution.events) == representative_inputs["fraud_evolution"]

    # Check all evidence items preserved
    assert list(summary.evidence.evidence_items) == representative_inputs["evidence"]


@pytest.mark.asyncio
async def test_async_build_summary_with_mock_timeline_service(representative_inputs):
    """
    Test async build_summary method orchestrating TimelineService.
    """
    mock_timeline_response = TimelineResponse(
        investigation_target="+919876543210",
        total_events=2,
        start_time=representative_inputs["events"][0].timestamp,
        end_time=representative_inputs["events"][-1].timestamp,
        events=representative_inputs["events"],
        entity_first_seen=representative_inputs["entity_info"],
        statistics=representative_inputs["statistics"],
        insights=representative_inputs["insights"],
        fraud_evolution=representative_inputs["fraud_evolution"],
        evidence=representative_inputs["evidence"],
    )

    mock_timeline_service = MagicMock(spec=TimelineService)
    mock_timeline_service.build_timeline = AsyncMock(return_value=mock_timeline_response)

    service = InvestigationSummaryService(timeline_service=mock_timeline_service)

    summary = await service.build_summary("+919876543210", target_type="phone")

    mock_timeline_service.build_timeline.assert_awaited_once_with("+919876543210")
    assert summary.metadata.target_value == "+919876543210"
    assert summary.overview.total_complaints == 2
    assert summary.overview.overall_risk_level == "HIGH"


def test_empty_inputs_handling():
    """
    Test that empty inputs construct a valid low-risk canonical summary.
    """
    service = InvestigationSummaryService()

    summary = service.create_summary_from_outputs(target_value="empty_target")

    assert summary.metadata.target_value == "empty_target"
    assert summary.overview.total_complaints == 0
    assert summary.overview.total_entities == 0
    assert summary.overview.overall_risk_level == "LOW"
    assert summary.timeline.total_events == 0
    assert summary.entities.total_entities == 0
    assert summary.evolution.total_evolution_events == 0
    assert summary.evidence.total_evidence_units == 0
    assert len(summary.recommendations) == 1
    assert summary.recommendations[0].action == "Maintain Standard System Monitoring"
    assert summary.recommendations[0].trigger == "STANDARD_MONITORING"
    assert summary.data_quality.overall_data_quality == "HIGH"


def test_data_quality_metrics_detection():
    """
    Test deterministic data quality metrics computation for timeline gaps and isolated entities.
    """
    service = InvestigationSummaryService()
    t1 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc)  # Gap > 30 days

    events = [
        TimelineEvent(
            event_type=TimelineEventType.COMPLAINT_CREATED,
            timestamp=t1,
            title="Event 1",
            description="Initial event",
            metadata={"complaint_id": "C-1"},
        ),
        TimelineEvent(
            event_type=TimelineEventType.COMPLAINT_CREATED,
            timestamp=t2,
            title="Event 2",
            description="Delayed event",
            metadata={"complaint_id": "C-2"},
        ),
    ]

    entity_info = [
        EntityTimelineInfo(
            entity_type="Phone",
            entity_value="+910000000000",
            first_seen=t1,
            first_seen_complaint="C-1",
            usage_count=1,
            complaint_ids=["C-1"],
        )
    ]

    summary = service.create_summary_from_outputs(
        target_value="test_dq",
        events=events,
        entity_info=entity_info,
    )

    assert len(summary.data_quality.timeline_gaps) == 1
    assert "+910000000000" in summary.data_quality.isolated_entities
