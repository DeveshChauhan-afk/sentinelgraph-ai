from __future__ import annotations

from datetime import datetime

from app.schemas.timeline import (
    EntityTimelineInfo,
    EvidenceSeverity,
    EvidenceType,
    EvolutionEventType,
    FraudEvolutionEvent,
)
from app.services.evidence_engine import EvidenceEngine


def test_threshold_based_entity_reuse_severity():
    """
    Test threshold-based severity mapping:
    - Reuse 3 to 4 => MEDIUM
    - Reuse 5 to 9 => HIGH
    - Reuse 10+    => CRITICAL
    """
    engine = EvidenceEngine()
    t1 = datetime(2026, 1, 1, 10, 0, 0)

    entity_info = [
        EntityTimelineInfo(
            entity_type="Phone",
            entity_value="+919876543210",
            first_seen=t1,
            first_seen_complaint="c-1",
            usage_count=3,
            complaint_ids=["c-1", "c-2", "c-3"],
        ),
        EntityTimelineInfo(
            entity_type="Phone",
            entity_value="+911111111111",
            first_seen=t1,
            first_seen_complaint="c-1",
            usage_count=6,
            complaint_ids=["c-1", "c-2", "c-3", "c-4", "c-5", "c-6"],
        ),
        EntityTimelineInfo(
            entity_type="UPI",
            entity_value="heavy@upi",
            first_seen=t1,
            first_seen_complaint="c-1",
            usage_count=12,
            complaint_ids=[f"c-{i}" for i in range(1, 13)],
        ),
    ]

    evidence = engine.build_evidence(
        timeline_events=[],
        entity_info=entity_info,
        timeline_statistics=None,
        timeline_insights=[],
        fraud_evolution=[],
    )

    assert len(evidence) == 3

    # Check 3-4 usage -> MEDIUM
    medium_ev = next(ev for ev in evidence if ev.supporting_entities == ["+919876543210"])
    assert medium_ev.severity == EvidenceSeverity.MEDIUM

    # Check 5-9 usage -> HIGH
    high_ev = next(ev for ev in evidence if ev.supporting_entities == ["+911111111111"])
    assert high_ev.severity == EvidenceSeverity.HIGH

    # Check 10+ usage -> CRITICAL
    critical_ev = next(ev for ev in evidence if ev.supporting_entities == ["heavy@upi"])
    assert critical_ev.severity == EvidenceSeverity.CRITICAL


def test_supporting_complaints_completeness():
    """
    Test that supporting_complaints includes all complaint IDs supporting the evidence.
    """
    engine = EvidenceEngine()
    t1 = datetime(2026, 1, 1, 10, 0, 0)
    all_c_ids = ["c-1", "c-2", "c-3", "c-4", "c-5"]

    entity_info = [
        EntityTimelineInfo(
            entity_type="BankAccount",
            entity_value="ACC123456",
            first_seen=t1,
            first_seen_complaint="c-1",
            usage_count=5,
            complaint_ids=all_c_ids,
        )
    ]

    evidence = engine.build_evidence(
        timeline_events=[],
        entity_info=entity_info,
        timeline_statistics=None,
        timeline_insights=[],
        fraud_evolution=[],
    )

    assert len(evidence) == 1
    assert evidence[0].supporting_complaints == all_c_ids


def test_every_network_expanded_event_generates_evidence():
    """
    Test that every NETWORK_EXPANDED fraud evolution event generates a corresponding NETWORK_EXPANSION evidence object.
    """
    engine = EvidenceEngine()
    t1 = datetime(2026, 1, 5, 10, 0, 0)
    t2 = datetime(2026, 1, 10, 10, 0, 0)

    fraud_evolution = [
        FraudEvolutionEvent(
            event_type=EvolutionEventType.NETWORK_EXPANDED,
            timestamp=t1,
            title="Network Expanded",
            description="Complaint c-2 introduced 2 new entities into the network.",
            related_entities=["+919999999999", "mule@upi"],
            related_complaints=["c-2"],
        ),
        FraudEvolutionEvent(
            event_type=EvolutionEventType.NETWORK_EXPANDED,
            timestamp=t2,
            title="Network Expanded",
            description="Complaint c-3 introduced 1 new entity into the network.",
            related_entities=["phish@domain.com"],
            related_complaints=["c-3"],
        ),
    ]

    evidence = engine.build_evidence(
        timeline_events=[],
        entity_info=[],
        timeline_statistics=None,
        timeline_insights=[],
        fraud_evolution=fraud_evolution,
    )

    expansion_evidence = [ev for ev in evidence if ev.evidence_type == EvidenceType.NETWORK_EXPANSION]
    assert len(expansion_evidence) == 2
    assert expansion_evidence[0].supporting_complaints == ["c-2"]
    assert expansion_evidence[1].supporting_complaints == ["c-3"]


def test_payment_and_communication_expansion_evidence():
    """
    Test evidence generation for payment and communication expansion evolution events.
    """
    engine = EvidenceEngine()
    t1 = datetime(2026, 1, 10, 10, 0, 0)

    fraud_evolution = [
        FraudEvolutionEvent(
            event_type=EvolutionEventType.PAYMENT_INFRASTRUCTURE_EXPANDED,
            timestamp=t1,
            title="Payment Infrastructure Expanded",
            description="Payment infrastructure expanded with new BankAccount identifier 'ACC999'.",
            related_entities=["ACC999"],
            related_complaints=["c-10"],
        ),
        FraudEvolutionEvent(
            event_type=EvolutionEventType.COMMUNICATION_CHANNEL_EXPANDED,
            timestamp=t1,
            title="Communication Channel Expanded",
            description="Communication channel expanded with new Email identifier 'phish@domain.com'.",
            related_entities=["phish@domain.com"],
            related_complaints=["c-10"],
        ),
    ]

    evidence = engine.build_evidence(
        timeline_events=[],
        entity_info=[],
        timeline_statistics=None,
        timeline_insights=[],
        fraud_evolution=fraud_evolution,
    )

    assert len(evidence) == 2

    pay_ev = next(ev for ev in evidence if ev.evidence_type == EvidenceType.PAYMENT_EXPANSION)
    assert pay_ev.severity == EvidenceSeverity.HIGH
    assert pay_ev.supporting_entities == ["ACC999"]

    comm_ev = next(ev for ev in evidence if ev.evidence_type == EvidenceType.COMMUNICATION_EXPANSION)
    assert comm_ev.severity == EvidenceSeverity.MEDIUM
    assert comm_ev.supporting_entities == ["phish@domain.com"]


def test_milestone_evidence_severity_mapping():
    """
    Test evidence severity assignment across different milestone thresholds (5, 20, 50, 100).
    """
    engine = EvidenceEngine()
    t1 = datetime(2026, 1, 1, 10, 0, 0)

    fraud_evolution = [
        FraudEvolutionEvent(
            event_type=EvolutionEventType.NETWORK_MILESTONE,
            timestamp=t1,
            title="Network Milestone: 5 Complaints",
            description="Fraud network reached a structural milestone of 5 connected complaints.",
            related_complaints=["c-5"],
            metadata={"milestone": 5},
        ),
        FraudEvolutionEvent(
            event_type=EvolutionEventType.NETWORK_MILESTONE,
            timestamp=t1,
            title="Network Milestone: 20 Complaints",
            description="Fraud network reached a structural milestone of 20 connected complaints.",
            related_complaints=["c-20"],
            metadata={"milestone": 20},
        ),
        FraudEvolutionEvent(
            event_type=EvolutionEventType.NETWORK_MILESTONE,
            timestamp=t1,
            title="Network Milestone: 50 Complaints",
            description="Fraud network reached a structural milestone of 50 connected complaints.",
            related_complaints=["c-50"],
            metadata={"milestone": 50},
        ),
        FraudEvolutionEvent(
            event_type=EvolutionEventType.NETWORK_MILESTONE,
            timestamp=t1,
            title="Network Milestone: 100 Complaints",
            description="Fraud network reached a structural milestone of 100 connected complaints.",
            related_complaints=["c-100"],
            metadata={"milestone": 100},
        ),
    ]

    evidence = engine.build_evidence(
        timeline_events=[],
        entity_info=[],
        timeline_statistics=None,
        timeline_insights=[],
        fraud_evolution=fraud_evolution,
    )

    assert len(evidence) == 4

    m5 = next(ev for ev in evidence if ev.metadata.get("milestone") == 5)
    assert m5.severity == EvidenceSeverity.LOW

    m20 = next(ev for ev in evidence if ev.metadata.get("milestone") == 20)
    assert m20.severity == EvidenceSeverity.MEDIUM

    m50 = next(ev for ev in evidence if ev.metadata.get("milestone") == 50)
    assert m50.severity == EvidenceSeverity.HIGH

    m100 = next(ev for ev in evidence if ev.metadata.get("milestone") == 100)
    assert m100.severity == EvidenceSeverity.CRITICAL


def test_confidence_calculation_and_clamping():
    """
    Test deterministic confidence calculation helper ensuring output stays strictly within [0.0, 1.0].
    """
    engine = EvidenceEngine()

    # Normal case
    conf = engine._calculate_confidence(
        base_confidence=0.75,
        supporting_complaints=["c-1", "c-2", "c-3"],
        supporting_entities=["e-1", "e-2"],
        usage_count=3,
    )
    assert 0.75 <= conf <= 1.0

    # Over-clamping case
    conf_max = engine._calculate_confidence(
        base_confidence=0.98,
        supporting_complaints=[f"c-{i}" for i in range(50)],
        supporting_entities=[f"e-{i}" for i in range(50)],
        usage_count=20,
    )
    assert conf_max == 1.0

    # Under-clamping case
    conf_min = engine._calculate_confidence(
        base_confidence=0.0,
        supporting_complaints=[],
        supporting_entities=[],
    )
    assert conf_min == 0.0


def test_empty_investigation():
    """
    Test that empty inputs return an empty evidence list.
    """
    engine = EvidenceEngine()
    assert engine.build_evidence([], [], None, [], []) == []
