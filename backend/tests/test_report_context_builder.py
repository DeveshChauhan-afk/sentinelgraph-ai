"""
Unit tests for ReportContextBuilder & InvestigationReportContext (Sprint 9 Phase 2).

Validates token optimization, report-oriented view model generation, timeline highlights,
entity ranking, evolution summarization, typed finding transformation, recommendation preservation,
supporting evidence filtering, citation mapping, immutability, and empty investigation handling.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.investigation_report_context import (
    InvestigationReportContext,
    ReportCitationItem,
    ReportContextExecutiveStatistics,
    ReportContextMetadata,
    ReportContextOverview,
    ReportCriticalFinding,
    ReportEntityHighlights,
    ReportEvolutionHighlights,
    ReportRecommendation,
    ReportSupportingEvidence,
    ReportTimelineHighlights,
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
    TimelineStatistics,
)
from app.services.investigation_summary_service import InvestigationSummaryService
from app.services.report_context_builder import ReportContextBuilder


@pytest.fixture
def sample_summary():
    """
    Fixture creating a representative InvestigationSummary for context building tests.
    """
    t1 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 5, 12, 0, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 1, 10, 15, 0, 0, tzinfo=timezone.utc)

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
            title="Payment Event: C-102",
            description="Complaint C-102 registered with scammer@upi",
            metadata={"complaint_id": "C-102"},
        ),
        TimelineEvent(
            event_type=TimelineEventType.COMPLAINT_CREATED,
            timestamp=t3,
            title="Network Milestone Expansion",
            description="Complaint C-103 expanded network to 10 complaints",
            metadata={"complaint_id": "C-103"},
        ),
    ]

    entity_info = [
        EntityTimelineInfo(
            entity_type="Phone",
            entity_value="+919876543210",
            first_seen=t1,
            first_seen_complaint="C-101",
            usage_count=6,
            complaint_ids=["C-101", "C-102", "C-103"],
        ),
        EntityTimelineInfo(
            entity_type="UPI",
            entity_value="scammer@upi",
            first_seen=t2,
            first_seen_complaint="C-102",
            usage_count=4,
            complaint_ids=["C-102", "C-103"],
        ),
        EntityTimelineInfo(
            entity_type="Email",
            entity_value="phish@scam.com",
            first_seen=t1,
            first_seen_complaint="C-101",
            usage_count=1,
            complaint_ids=["C-101"],
        ),
    ]

    statistics = TimelineStatistics(
        total_complaints=3,
        total_entities=3,
        phones=1,
        upis=1,
        emails=1,
        urls=0,
        bank_accounts=0,
        organizations=0,
        people=0,
        locations=0,
    )

    insights = [
        TimelineInsight(
            title="Entity Reuse Detected",
            description="Phone number reused across 6 complaints.",
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
            confidence=0.88,
            title="High Entity Reuse: Phone '+919876543210'",
            description="Phone '+919876543210' reused across 6 complaints.",
            supporting_entities=["+919876543210"],
            supporting_complaints=["C-101", "C-102", "C-103"],
        ),
        InvestigationEvidence(
            evidence_type=EvidenceType.PAYMENT_EXPANSION,
            severity=EvidenceSeverity.HIGH,
            confidence=0.82,
            title="Payment Infrastructure Expansion",
            description="Payment infrastructure expanded with scammer@upi.",
            supporting_entities=["scammer@upi"],
            supporting_complaints=["C-102"],
        ),
    ]

    summary_service = InvestigationSummaryService()
    return summary_service.create_summary_from_outputs(
        target_value="+919876543210",
        target_type="phone",
        events=events,
        entity_info=entity_info,
        statistics=statistics,
        insights=insights,
        fraud_evolution=fraud_evolution,
        evidence=evidence,
    )


def test_build_report_context_structure(sample_summary):
    """
    Test report context construction and schema types.
    """
    builder = ReportContextBuilder()
    context = builder.build_report_context(sample_summary)

    assert isinstance(context, InvestigationReportContext)
    assert isinstance(context.metadata, ReportContextMetadata)
    assert isinstance(context.overview, ReportContextOverview)
    assert isinstance(context.executive_statistics, ReportContextExecutiveStatistics)
    assert isinstance(context.timeline_highlights, ReportTimelineHighlights)
    assert isinstance(context.entity_highlights, ReportEntityHighlights)
    assert isinstance(context.evolution_highlights, ReportEvolutionHighlights)
    assert isinstance(context.critical_findings, tuple)
    assert isinstance(context.recommendations, tuple)
    assert isinstance(context.supporting_evidence, tuple)
    assert isinstance(context.citation_map, tuple)


def test_metadata_generation(sample_summary):
    """
    Test metadata generation in report context.
    """
    builder = ReportContextBuilder()
    context = builder.build_report_context(sample_summary)

    assert context.metadata.report_context_version == "1.0"
    assert context.metadata.generated_by == "ReportContextBuilder"
    assert context.metadata.generated_from_summary_version == sample_summary.metadata.summary_version


def test_timeline_highlights_selection(sample_summary):
    """
    Test compact timeline highlights selection and categories.
    """
    builder = ReportContextBuilder()
    context = builder.build_report_context(sample_summary)

    highlights = context.timeline_highlights.highlights
    assert len(highlights) > 0
    categories = [h.category for h in highlights]
    assert "FIRST_OBSERVED" in categories
    assert "LATEST_OBSERVED" in categories


def test_entity_highlights_ranking(sample_summary):
    """
    Test entity ranking by usage count and rank reason assignment.
    """
    builder = ReportContextBuilder()
    context = builder.build_report_context(sample_summary)

    highlights = context.entity_highlights.highlights
    assert len(highlights) == 3
    # First entity should be highest usage count (+919876543210 with 6 usages)
    assert highlights[0].entity_value == "+919876543210"
    assert highlights[0].rank_reason == "HIGH_REUSE_PHONE"
    assert highlights[1].entity_value == "scammer@upi"
    assert highlights[1].rank_reason == "HIGH_REUSE_UPI"


def test_evolution_summarization(sample_summary):
    """
    Test evolution chronology highlights.
    """
    builder = ReportContextBuilder()
    context = builder.build_report_context(sample_summary)

    evolution = context.evolution_highlights
    assert evolution.network_origin is not None
    assert len(evolution.payment_expansion) == 1
    assert "scammer@upi" in evolution.payment_expansion[0]


def test_finding_transformation_and_provenance(sample_summary):
    """
    Test transformation of findings preserving IDs and provenance.
    """
    builder = ReportContextBuilder()
    context = builder.build_report_context(sample_summary)

    findings = context.critical_findings
    assert len(findings) == len(sample_summary.findings)

    first_finding = findings[0]
    assert isinstance(first_finding, ReportCriticalFinding)
    assert len(first_finding.supporting_complaint_ids) > 0
    assert len(first_finding.supporting_evidence_ids) > 0


def test_recommendations_preservation(sample_summary):
    """
    Test preservation of explainable recommendations with triggers.
    """
    builder = ReportContextBuilder()
    context = builder.build_report_context(sample_summary)

    recs = context.recommendations
    assert len(recs) == len(sample_summary.recommendations)

    rec = recs[0]
    assert isinstance(rec, ReportRecommendation)
    assert rec.trigger != ""
    assert rec.priority in ("HIGH", "MEDIUM", "LOW")
    assert len(rec.affected_entities) > 0


def test_citation_map_generation(sample_summary):
    """
    Test structured citation map generation linking finding IDs to complaint and entity IDs.
    """
    builder = ReportContextBuilder()
    context = builder.build_report_context(sample_summary)

    citations = context.citation_map
    assert len(citations) == len(sample_summary.findings)

    c0 = citations[0]
    assert isinstance(c0, ReportCitationItem)
    assert c0.finding_id == sample_summary.findings[0].finding_id
    assert c0.complaint_ids == sample_summary.findings[0].supporting_complaint_ids


def test_supporting_evidence_filtering(sample_summary):
    """
    Test filtering to include materially supporting high-severity / high-confidence evidence.
    """
    builder = ReportContextBuilder()
    context = builder.build_report_context(sample_summary)

    evidence = context.supporting_evidence
    assert len(evidence) == 2
    assert all(isinstance(e, ReportSupportingEvidence) for e in evidence)
    assert all(e.confidence >= 0.75 for e in evidence)


def test_immutability(sample_summary):
    """
    Test that InvestigationReportContext is strictly read-only and immutable.
    """
    builder = ReportContextBuilder()
    context = builder.build_report_context(sample_summary)

    with pytest.raises((ValidationError, AttributeError, TypeError)):
        context.metadata = ReportContextMetadata()

    with pytest.raises((ValidationError, AttributeError, TypeError)):
        context.overview.overall_risk_level = "LOW"


@pytest.mark.asyncio
async def test_async_builder_support(sample_summary):
    """
    Test async build_report_context_async method.
    """
    builder = ReportContextBuilder()
    context = await builder.build_report_context_async(sample_summary)
    assert context.overview.target_value == "+919876543210"


def test_empty_investigation_summary_handling():
    """
    Test building ReportContext from an empty InvestigationSummary.
    """
    summary_service = InvestigationSummaryService()
    empty_summary = summary_service.create_summary_from_outputs(target_value="empty_target")

    builder = ReportContextBuilder()
    context = builder.build_report_context(empty_summary)

    assert context.overview.target_value == "empty_target"
    assert context.overview.overall_risk_level == "LOW"
    assert context.timeline_highlights.total_highlights == 0
    assert context.entity_highlights.total_highlights == 0
    assert len(context.recommendations) == 1
    assert context.recommendations[0].trigger == "STANDARD_MONITORING"
