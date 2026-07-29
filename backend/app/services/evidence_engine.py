"""
Evidence Engine Service.

Transforms timeline, entity evolution, statistics, deterministic insights, and
fraud evolution outputs into structured, explainable investigation evidence units with
deterministic confidence scoring.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.schemas.timeline import (
    EntityTimelineInfo,
    EvidenceSeverity,
    EvidenceType,
    EvolutionEventType,
    FraudEvolutionEvent,
    InvestigationEvidence,
    TimelineEvent,
    TimelineInsight,
    TimelineStatistics,
)


class EvidenceEngine:
    """
    Deterministic engine for building structured investigation evidence.
    """

    def build_evidence(
        self,
        timeline_events: list[TimelineEvent],
        entity_info: list[EntityTimelineInfo],
        timeline_statistics: TimelineStatistics | None,
        timeline_insights: list[TimelineInsight],
        fraud_evolution: list[FraudEvolutionEvent],
    ) -> list[InvestigationEvidence]:
        """
        Synthesize analysis outputs into structured investigation evidence units.

        Args:
            timeline_events:
                Chronological list of timeline events.
            entity_info:
                Entity lifecycle and usage frequency data.
            timeline_statistics:
                Investigation statistical summary.
            timeline_insights:
                Deterministic timeline insights.
            fraud_evolution:
                Fraud network evolution events.

        Returns:
            List of InvestigationEvidence units.
        """
        logger.info(
            "Building investigation evidence from timeline data (events={}, entities={}, evolution={}).",
            len(timeline_events),
            len(entity_info),
            len(fraud_evolution),
        )

        evidence_list: list[InvestigationEvidence] = []

        # 1. Entity Reuse Evidence (Threshold-based Severity: 3-4 = MEDIUM, 5-9 = HIGH, 10+ = CRITICAL)
        for info in entity_info:
            if info.usage_count >= 3:
                if info.usage_count >= 10:
                    severity = EvidenceSeverity.CRITICAL
                    base_conf = 0.92
                    title_prefix = "Critical Entity Reuse"
                elif info.usage_count >= 5:
                    severity = EvidenceSeverity.HIGH
                    base_conf = 0.85
                    title_prefix = "High Entity Reuse"
                else:
                    severity = EvidenceSeverity.MEDIUM
                    base_conf = 0.75
                    title_prefix = "Entity Reuse"

                title = f"{title_prefix}: {info.entity_type} '{info.entity_value}'"
                desc = (
                    f"{info.entity_type} '{info.entity_value}' reused across "
                    f"{info.usage_count} complaints."
                )

                # Ensure supporting_complaints includes all complaint IDs supporting this entity
                supp_c = (
                    list(info.complaint_ids)
                    if info.complaint_ids
                    else ([info.first_seen_complaint] if info.first_seen_complaint else [])
                )

                conf = self._calculate_confidence(
                    base_confidence=base_conf,
                    supporting_complaints=supp_c,
                    supporting_entities=[info.entity_value],
                    usage_count=info.usage_count,
                )

                evidence_list.append(
                    InvestigationEvidence(
                        evidence_type=EvidenceType.ENTITY_REUSE,
                        severity=severity,
                        confidence=conf,
                        title=title,
                        description=desc,
                        supporting_entities=[info.entity_value],
                        supporting_complaints=supp_c,
                        metadata={
                            "entity_type": info.entity_type,
                            "lookup_value": info.entity_value,
                            "usage_count": info.usage_count,
                            "complaint_ids": supp_c,
                        },
                    )
                )

        # 2. Fraud Evolution Evidence Generation (Payment, Communication, Network Expansion, Milestones)
        for ev in fraud_evolution:
            if ev.event_type == EvolutionEventType.PAYMENT_INFRASTRUCTURE_EXPANDED:
                conf = self._calculate_confidence(
                    base_confidence=0.85,
                    supporting_complaints=ev.related_complaints,
                    supporting_entities=ev.related_entities,
                )
                evidence_list.append(
                    InvestigationEvidence(
                        evidence_type=EvidenceType.PAYMENT_EXPANSION,
                        severity=EvidenceSeverity.HIGH,
                        confidence=conf,
                        title="Payment Infrastructure Expansion",
                        description=ev.description,
                        supporting_entities=ev.related_entities,
                        supporting_complaints=ev.related_complaints,
                        metadata=ev.metadata,
                    )
                )
            elif ev.event_type == EvolutionEventType.COMMUNICATION_CHANNEL_EXPANDED:
                conf = self._calculate_confidence(
                    base_confidence=0.80,
                    supporting_complaints=ev.related_complaints,
                    supporting_entities=ev.related_entities,
                )
                evidence_list.append(
                    InvestigationEvidence(
                        evidence_type=EvidenceType.COMMUNICATION_EXPANSION,
                        severity=EvidenceSeverity.MEDIUM,
                        confidence=conf,
                        title="Communication Channel Expansion",
                        description=ev.description,
                        supporting_entities=ev.related_entities,
                        supporting_complaints=ev.related_complaints,
                        metadata=ev.metadata,
                    )
                )
            elif ev.event_type == EvolutionEventType.NETWORK_EXPANDED:
                severity = (
                    EvidenceSeverity.HIGH
                    if len(ev.related_entities) >= 3
                    else EvidenceSeverity.MEDIUM
                )
                conf = self._calculate_confidence(
                    base_confidence=0.80,
                    supporting_complaints=ev.related_complaints,
                    supporting_entities=ev.related_entities,
                )
                evidence_list.append(
                    InvestigationEvidence(
                        evidence_type=EvidenceType.NETWORK_EXPANSION,
                        severity=severity,
                        confidence=conf,
                        title="Network Expanded via Complaint",
                        description=ev.description,
                        supporting_entities=ev.related_entities,
                        supporting_complaints=ev.related_complaints,
                        metadata=ev.metadata,
                    )
                )
            elif ev.event_type == EvolutionEventType.NETWORK_MILESTONE:
                milestone_count = ev.metadata.get("milestone", 0)
                if milestone_count >= 100:
                    severity = EvidenceSeverity.CRITICAL
                    base_conf = 0.95
                elif milestone_count >= 50:
                    severity = EvidenceSeverity.HIGH
                    base_conf = 0.90
                elif milestone_count >= 20:
                    severity = EvidenceSeverity.MEDIUM
                    base_conf = 0.85
                else:
                    severity = EvidenceSeverity.LOW
                    base_conf = 0.70

                conf = self._calculate_confidence(
                    base_confidence=base_conf,
                    supporting_complaints=ev.related_complaints,
                    supporting_entities=ev.related_entities,
                )
                evidence_list.append(
                    InvestigationEvidence(
                        evidence_type=EvidenceType.NETWORK_MILESTONE,
                        severity=severity,
                        confidence=conf,
                        title=ev.title,
                        description=ev.description,
                        supporting_complaints=ev.related_complaints,
                        supporting_entities=ev.related_entities,
                        metadata=ev.metadata,
                    )
                )

        # 3. Overall Large Network Evidence (if total_complaints >= 20)
        if timeline_statistics and timeline_statistics.total_complaints >= 20:
            supp_c_all = [
                event.metadata["complaint_id"]
                for event in timeline_events
                if "complaint_id" in event.metadata
            ]
            conf = self._calculate_confidence(
                base_confidence=0.90,
                supporting_complaints=supp_c_all,
                supporting_entities=[],
                usage_count=timeline_statistics.total_complaints,
            )
            evidence_list.append(
                InvestigationEvidence(
                    evidence_type=EvidenceType.NETWORK_EXPANSION,
                    severity=EvidenceSeverity.HIGH,
                    confidence=conf,
                    title="Large-Scale Coordinated Fraud Network",
                    description=(
                        f"Investigated network connects {timeline_statistics.total_complaints} "
                        f"complaints across {timeline_statistics.total_entities} distinct entities."
                    ),
                    supporting_complaints=supp_c_all,  # Include all supporting complaints
                    metadata={"total_complaints": timeline_statistics.total_complaints},
                )
            )

        # Deduplicate evidence objects based on title and description
        deduped_evidence: list[InvestigationEvidence] = []
        seen_signatures: set[tuple[str, str]] = set()

        for ev_item in evidence_list:
            sig = (ev_item.title, ev_item.description)
            if sig not in seen_signatures:
                seen_signatures.add(sig)
                deduped_evidence.append(ev_item)

        logger.info(
            "Constructed {} structured investigation evidence units.",
            len(deduped_evidence),
        )

        return deduped_evidence

    def _calculate_confidence(
        self,
        base_confidence: float,
        supporting_complaints: list[str],
        supporting_entities: list[str],
        supporting_events: list[str] | None = None,
        usage_count: int = 1,
    ) -> float:
        """
        Calculate deterministic confidence score based on evidence strength metrics.
        Clamps result strictly to range [0.0, 1.0].

        Args:
            base_confidence:
                Base confidence score for the rule.
            supporting_complaints:
                Supporting complaint IDs.
            supporting_entities:
                Supporting entity lookup values.
            supporting_events:
                Supporting event descriptors.
            usage_count:
                Number of occurrences or usages.

        Returns:
            Clamped confidence float between 0.0 and 1.0.
        """
        score = base_confidence

        if usage_count > 1:
            score += min(0.10, (usage_count - 1) * 0.01)

        c_count = len(supporting_complaints)
        e_count = len(supporting_entities)
        ev_count = len(supporting_events) if supporting_events else 0

        if c_count > 1:
            score += min(0.08, (c_count - 1) * 0.01)
        if e_count > 1:
            score += min(0.04, (e_count - 1) * 0.005)
        if ev_count > 0:
            score += min(0.03, ev_count * 0.005)

        clamped = max(0.0, min(1.0, score))
        return round(clamped, 2)
