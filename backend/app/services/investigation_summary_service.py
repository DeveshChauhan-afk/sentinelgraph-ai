"""
Investigation Summary Service Architecture (Sprint 9 Phase 1.5 Refinements).

Service responsible for assembling the canonical immutable InvestigationSummary object ('Case File DTO')
from deterministic analysis outputs. Refactored into modular private helpers for facts, presentation,
typed findings, recommendation provenance, evidence metrics, data quality, and immutability.
"""

from __future__ import annotations

from datetime import datetime
from loguru import logger

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
    FraudEvolutionEvent,
    InvestigationEvidence,
    TimelineEvent,
    TimelineInsight,
    TimelineResponse,
    TimelineStatistics,
)
from app.services.entity_analysis_service import EntityAnalysisService
from app.services.evidence_engine import EvidenceEngine
from app.services.fraud_evolution_service import FraudEvolutionService
from app.services.timeline_analysis_service import TimelineAnalysisService
from app.services.timeline_service import TimelineService


class InvestigationSummaryService:
    """
    Service responsible for constructing canonical immutable InvestigationSummary DTOs
    from deterministic outputs across all analysis engines.
    """

    def __init__(
        self,
        timeline_service: TimelineService | None = None,
        entity_analysis_service: EntityAnalysisService | None = None,
        timeline_analysis_service: TimelineAnalysisService | None = None,
        fraud_evolution_service: FraudEvolutionService | None = None,
        evidence_engine: EvidenceEngine | None = None,
    ) -> None:
        """
        Initialize InvestigationSummaryService with dependency injection.

        Args:
            timeline_service: Optional TimelineService instance for full orchestration.
            entity_analysis_service: Optional EntityAnalysisService instance.
            timeline_analysis_service: Optional TimelineAnalysisService instance.
            fraud_evolution_service: Optional FraudEvolutionService instance.
            evidence_engine: Optional EvidenceEngine instance.
        """
        self._timeline_service = timeline_service
        self._entity_analysis_service = (
            entity_analysis_service or EntityAnalysisService()
        )
        self._timeline_analysis_service = (
            timeline_analysis_service or TimelineAnalysisService()
        )
        self._fraud_evolution_service = (
            fraud_evolution_service or FraudEvolutionService()
        )
        self._evidence_engine = evidence_engine or EvidenceEngine()

    async def build_summary(
        self,
        entity_value: str,
        target_type: str | None = None,
    ) -> InvestigationSummary:
        """
        Orchestrate complete summary generation for an investigation target.

        Args:
            entity_value: Target identifier (e.g. phone, email, upi, complaint_id).
            target_type: Optional entity type classification.

        Returns:
            Canonical InvestigationSummary object.
        """
        logger.info(
            "Building canonical InvestigationSummary (target_type={}).",
            target_type or "unspecified",
        )

        if self._timeline_service is None:
            logger.warning(
                "TimelineService instance is None for build_summary. Falling back to deterministic summary creation."
            )
            return self.create_summary_from_outputs(
                target_value=entity_value,
                target_type=target_type,
            )

        timeline_response: TimelineResponse = (
            await self._timeline_service.build_timeline(entity_value)
        )

        return self.create_summary_from_outputs(
            target_value=entity_value,
            target_type=target_type,
            timeline_response=timeline_response,
        )

    def create_summary_from_outputs(
        self,
        target_value: str,
        target_type: str | None = None,
        timeline_response: TimelineResponse | None = None,
        events: list[TimelineEvent] | None = None,
        entity_info: list[EntityTimelineInfo] | None = None,
        statistics: TimelineStatistics | None = None,
        insights: list[TimelineInsight] | None = None,
        fraud_evolution: list[FraudEvolutionEvent] | None = None,
        evidence: list[InvestigationEvidence] | None = None,
    ) -> InvestigationSummary:
        """
        Pure deterministic aggregation of analysis outputs into a canonical InvestigationSummary.

        Accepts either a TimelineResponse object or individual output parameters.
        Modularized into private builder helpers.

        Args:
            target_value: Target identifier being investigated.
            target_type: Optional target entity type.
            timeline_response: Optional full TimelineResponse from Sprint 8 TimelineService.
            events: Optional list of timeline events.
            entity_info: Optional list of entity evolution info records.
            statistics: Optional TimelineStatistics model.
            insights: Optional list of TimelineInsight models.
            fraud_evolution: Optional list of FraudEvolutionEvent models.
            evidence: Optional list of InvestigationEvidence models.

        Returns:
            Canonical InvestigationSummary object.
        """
        if timeline_response is not None:
            if events is None:
                events = timeline_response.events
            if entity_info is None:
                entity_info = timeline_response.entity_first_seen
            if statistics is None:
                statistics = timeline_response.statistics
            if insights is None:
                insights = timeline_response.insights
            if fraud_evolution is None:
                fraud_evolution = timeline_response.fraud_evolution
            if evidence is None:
                evidence = timeline_response.evidence

        events = events or []
        entity_info = entity_info or []
        insights = insights or []
        fraud_evolution = fraud_evolution or []
        evidence = evidence or []

        # 1. Metadata
        metadata = self._build_metadata(target_value=target_value, target_type=target_type)

        # 2. Timeline
        timeline_summary = self._build_timeline(events=events)

        # 3. Entities
        entity_summary = self._build_entities(entity_info=entity_info)
        reused_entities = [e for e in entity_info if e.usage_count > 1]

        # 4. Evolution
        evolution_summary = self._build_evolution(fraud_evolution=fraud_evolution)

        # 5. Evidence
        evidence_summary = self._build_evidence(evidence=evidence)

        # 6. Statistics
        investigation_statistics = self._build_statistics(
            statistics=statistics,
            entity_info=entity_info,
            events=events,
            total_entities=entity_summary.total_entities,
        )

        # 7. Risk Level Determination
        overall_risk_level = self._determine_overall_risk(
            evidence_summary=evidence_summary,
            stats_complaints=investigation_statistics.total_complaints,
            reused_count=entity_summary.reused_entities_count,
        )

        # 8. Overview (Facts only)
        overview = self._build_overview(
            target_value=target_value,
            stats_complaints=investigation_statistics.total_complaints,
            stats_entities=investigation_statistics.total_entities,
            start_time=timeline_summary.start_time,
            end_time=timeline_summary.end_time,
            overall_risk_level=overall_risk_level,
        )

        # 9. Findings (Typed with provenance)
        findings = self._build_findings(
            evidence=evidence,
            insights=insights,
            reused_entities=reused_entities,
            fraud_evolution=fraud_evolution,
        )

        # 10. Presentation (Narrative separation)
        presentation = self._build_presentation(
            target_value=target_value,
            stats_complaints=investigation_statistics.total_complaints,
            stats_entities=investigation_statistics.total_entities,
            duration_days=timeline_summary.duration_days,
            evidence_count=evidence_summary.total_evidence_units,
            critical_count=evidence_summary.critical_count,
            high_count=evidence_summary.high_count,
            medium_count=evidence_summary.medium_count,
            low_count=evidence_summary.low_count,
            overall_risk_level=overall_risk_level,
            findings=findings,
        )

        # 11. Recommendations (Explainable with triggers)
        recommendations = self._build_recommendations(
            reused_entities=reused_entities,
            overall_risk_level=overall_risk_level,
            evidence=evidence,
            target_value=target_value,
        )

        # 12. Data Quality
        data_quality = self._build_data_quality(
            events=events,
            entity_info=entity_info,
            statistics=statistics,
            fraud_evolution=fraud_evolution,
        )

        logger.info(
            "Constructed canonical InvestigationSummary (target_type={}): risk={}, findings={}, recommendations={}.",
            target_type or "unspecified",
            overall_risk_level,
            len(findings),
            len(recommendations),
        )

        return InvestigationSummary(
            metadata=metadata,
            overview=overview,
            presentation=presentation,
            statistics=investigation_statistics,
            timeline=timeline_summary,
            entities=entity_summary,
            evolution=evolution_summary,
            evidence=evidence_summary,
            data_quality=data_quality,
            findings=tuple(findings),
            recommendations=tuple(recommendations),
        )

    def _build_metadata(
        self,
        target_value: str,
        target_type: str | None,
    ) -> InvestigationMetadata:
        """Construct canonical InvestigationMetadata."""
        return InvestigationMetadata(
            target_value=target_value,
            target_type=target_type,
            summary_version="1.0",
            generated_by="InvestigationSummaryService",
        )

    def _build_overview(
        self,
        target_value: str,
        stats_complaints: int,
        stats_entities: int,
        start_time: datetime | None,
        end_time: datetime | None,
        overall_risk_level: str,
    ) -> InvestigationOverview:
        """Construct structured facts overview (excluding narrative text)."""
        return InvestigationOverview(
            target_value=target_value,
            total_complaints=stats_complaints,
            total_entities=stats_entities,
            time_range_start=start_time,
            time_range_end=end_time,
            overall_risk_level=overall_risk_level,
        )

    def _build_presentation(
        self,
        target_value: str,
        stats_complaints: int,
        stats_entities: int,
        duration_days: int,
        evidence_count: int,
        critical_count: int,
        high_count: int,
        medium_count: int,
        low_count: int,
        overall_risk_level: str,
        findings: list[InvestigationFinding],
    ) -> InvestigationPresentation:
        """Construct presentation narrative and key takeaways."""
        exec_summary = (
            f"Deterministic investigation summary for target '{target_value}'. "
            f"Analyzed {stats_complaints} connected complaints across {stats_entities} distinct entities over {duration_days} days. "
            f"Synthesized {evidence_count} evidence units yielding an overall risk level of {overall_risk_level}."
        )

        risk_justification = (
            f"Assigned risk level '{overall_risk_level}' based on {critical_count} critical, "
            f"{high_count} high, {medium_count} medium, and {low_count} low severity evidence units."
        )

        takeaways = [
            f"Target: {target_value}",
            f"Complaints connected: {stats_complaints}",
            f"Entities involved: {stats_entities}",
            f"Overall Risk Level: {overall_risk_level}",
        ]
        if findings:
            takeaways.append(f"Top Finding: {findings[0].title}")

        return InvestigationPresentation(
            executive_summary=exec_summary,
            risk_justification=risk_justification,
            key_takeaways=tuple(takeaways),
        )

    def _build_statistics(
        self,
        statistics: TimelineStatistics | None,
        entity_info: list[EntityTimelineInfo],
        events: list[TimelineEvent],
        total_entities: int,
    ) -> InvestigationStatistics:
        """Construct investigation statistics breakdown."""
        if statistics is not None:
            stats_complaints = statistics.total_complaints
            stats_entities = statistics.total_entities
            phones = statistics.phones
            upis = statistics.upis
            emails = statistics.emails
            urls = statistics.urls
            bank_accounts = statistics.bank_accounts
            organizations = statistics.organizations
            people = statistics.people
            locations = statistics.locations
        else:
            stats_complaints = len(
                {ev.metadata.get("complaint_id") for ev in events if "complaint_id" in ev.metadata}
            )
            stats_entities = total_entities
            phones = sum(1 for e in entity_info if e.entity_type.lower() == "phone")
            upis = sum(1 for e in entity_info if e.entity_type.lower() in ("upi", "upi_id"))
            emails = sum(1 for e in entity_info if e.entity_type.lower() == "email")
            urls = sum(1 for e in entity_info if e.entity_type.lower() == "url")
            bank_accounts = sum(1 for e in entity_info if e.entity_type.lower() in ("bankaccount", "bank_account"))
            organizations = sum(1 for e in entity_info if e.entity_type.lower() == "organization")
            people = sum(1 for e in entity_info if e.entity_type.lower() in ("person", "people"))
            locations = sum(1 for e in entity_info if e.entity_type.lower() == "location")

        entity_type_counts = {
            "phones": phones,
            "upis": upis,
            "emails": emails,
            "urls": urls,
            "bank_accounts": bank_accounts,
            "organizations": organizations,
            "people": people,
            "locations": locations,
        }

        return InvestigationStatistics(
            total_complaints=stats_complaints,
            total_entities=stats_entities,
            phones=phones,
            upis=upis,
            emails=emails,
            urls=urls,
            bank_accounts=bank_accounts,
            organizations=organizations,
            people=people,
            locations=locations,
            entity_type_counts=entity_type_counts,
        )

    def _build_timeline(self, events: list[TimelineEvent]) -> InvestigationTimelineSummary:
        """Construct chronological timeline summary."""
        total_events = len(events)
        start_time = events[0].timestamp if events else None
        end_time = events[-1].timestamp if events else None

        duration_days = 0
        if start_time and end_time:
            duration_days = max(0, (end_time - start_time).days)

        return InvestigationTimelineSummary(
            total_events=total_events,
            start_time=start_time,
            end_time=end_time,
            duration_days=duration_days,
            events=tuple(events),
        )

    def _build_entities(self, entity_info: list[EntityTimelineInfo]) -> InvestigationEntitySummary:
        """Construct entity evolution summary."""
        total_entities = len(entity_info)
        reused_entities_count = sum(1 for e in entity_info if e.usage_count > 1)
        return InvestigationEntitySummary(
            total_entities=total_entities,
            reused_entities_count=reused_entities_count,
            entities=tuple(entity_info),
        )

    def _build_evolution(self, fraud_evolution: list[FraudEvolutionEvent]) -> InvestigationEvolutionSummary:
        """Construct fraud evolution summary."""
        return InvestigationEvolutionSummary(
            total_evolution_events=len(fraud_evolution),
            events=tuple(fraud_evolution),
        )

    def _build_evidence(self, evidence: list[InvestigationEvidence]) -> InvestigationEvidenceSummary:
        """Construct evidence summary with aggregate metrics."""
        critical_count = 0
        high_count = 0
        medium_count = 0
        low_count = 0

        for item in evidence:
            sev = item.severity
            sev_str = sev.value if isinstance(sev, EvidenceSeverity) else str(sev).upper()
            if sev_str == "CRITICAL":
                critical_count += 1
            elif sev_str == "HIGH":
                high_count += 1
            elif sev_str == "MEDIUM":
                medium_count += 1
            else:
                low_count += 1

        confidences = [ev.confidence for ev in evidence]
        highest_confidence = max(confidences, default=0.0)
        average_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.0

        if critical_count > 0:
            highest_severity = "CRITICAL"
        elif high_count > 0:
            highest_severity = "HIGH"
        elif medium_count > 0:
            highest_severity = "MEDIUM"
        elif low_count > 0:
            highest_severity = "LOW"
        else:
            highest_severity = "NONE"

        return InvestigationEvidenceSummary(
            total_evidence_units=len(evidence),
            critical_count=critical_count,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            highest_confidence=highest_confidence,
            average_confidence=average_confidence,
            highest_severity=highest_severity,
            evidence_items=tuple(evidence),
        )

    def _determine_overall_risk(
        self,
        evidence_summary: InvestigationEvidenceSummary,
        stats_complaints: int,
        reused_count: int,
    ) -> str:
        """Determine overall risk level deterministically."""
        if evidence_summary.critical_count > 0:
            return "CRITICAL"
        if evidence_summary.high_count > 0 or stats_complaints >= 10:
            return "HIGH"
        if evidence_summary.medium_count > 0 or stats_complaints >= 3 or reused_count > 0:
            return "MEDIUM"
        return "LOW"

    def _build_findings(
        self,
        evidence: list[InvestigationEvidence],
        insights: list[TimelineInsight],
        reused_entities: list[EntityTimelineInfo],
        fraud_evolution: list[FraudEvolutionEvent],
    ) -> list[InvestigationFinding]:
        """Construct strongly typed findings with provenance citations."""
        findings: list[InvestigationFinding] = []

        # 1. Findings from synthesized Evidence units
        for idx, ev in enumerate(evidence, start=1):
            sev_val = ev.severity.value if isinstance(ev.severity, EvidenceSeverity) else str(ev.severity).upper()

            # Map evidence type to FindingType
            ev_type_str = ev.evidence_type.value if isinstance(ev.evidence_type, EvidenceType) else str(ev.evidence_type).upper()
            if ev_type_str == "ENTITY_REUSE":
                finding_type = FindingType.ENTITY_REUSE
            elif ev_type_str == "PAYMENT_EXPANSION":
                finding_type = FindingType.PAYMENT_EXPANSION
            elif ev_type_str == "COMMUNICATION_EXPANSION":
                finding_type = FindingType.COMMUNICATION_PATTERN
            elif ev_type_str in ("NETWORK_EXPANSION", "NETWORK_MILESTONE"):
                finding_type = FindingType.NETWORK_EXPANSION
            else:
                finding_type = FindingType.EVIDENCE

            findings.append(
                InvestigationFinding(
                    finding_id=f"FINDING-EVD-{idx:03d}",
                    type=finding_type,
                    severity=sev_val,
                    confidence=ev.confidence,
                    title=ev.title,
                    description=ev.description,
                    supporting_evidence_ids=(str(ev.evidence_id),),
                    supporting_complaint_ids=tuple(ev.supporting_complaints),
                    supporting_entity_ids=tuple(ev.supporting_entities),
                )
            )

        # 2. Findings from Timeline Insights
        for idx, insight in enumerate(insights, start=1):
            sev_val = insight.severity.value if hasattr(insight.severity, "value") else str(insight.severity).upper()
            title_lower = insight.title.lower()
            if "reuse" in title_lower:
                finding_type = FindingType.ENTITY_REUSE
            elif "duration" in title_lower:
                finding_type = FindingType.TIMELINE
            elif "phone" in title_lower or "payment" in title_lower:
                finding_type = FindingType.COMMUNICATION_PATTERN
            else:
                finding_type = FindingType.RISK

            findings.append(
                InvestigationFinding(
                    finding_id=f"FINDING-INS-{idx:03d}",
                    type=finding_type,
                    severity=sev_val,
                    confidence=0.90,
                    title=insight.title,
                    description=insight.description,
                    supporting_evidence_ids=(),
                    supporting_complaint_ids=(),
                    supporting_entity_ids=(),
                )
            )

        return findings

    def _build_recommendations(
        self,
        reused_entities: list[EntityTimelineInfo],
        overall_risk_level: str,
        evidence: list[InvestigationEvidence],
        target_value: str,
    ) -> list[InvestigationRecommendation]:
        """Construct explainable action recommendations with explicit triggers."""
        recommendations: list[InvestigationRecommendation] = []
        rec_counter = 1

        for info in reused_entities:
            e_type = info.entity_type.lower()
            if e_type in ("upi", "upi_id", "bankaccount", "bank_account"):
                recommendations.append(
                    InvestigationRecommendation(
                        recommendation_id=f"REC-{rec_counter:03d}",
                        action=f"Freeze/Block Payment Identifier '{info.entity_value}'",
                        priority="HIGH",
                        reason=f"Payment identifier reused across {info.usage_count} complaints.",
                        trigger="PAYMENT_EXPANSION",
                        target_entities=(info.entity_value,),
                    )
                )
                rec_counter += 1
            elif e_type in ("phone", "email"):
                recommendations.append(
                    InvestigationRecommendation(
                        recommendation_id=f"REC-{rec_counter:03d}",
                        action=f"Flag Identifier '{info.entity_value}' for Enhanced Monitoring",
                        priority="HIGH",
                        reason=f"Communication channel reused across {info.usage_count} complaints.",
                        trigger="ENTITY_REUSE_THRESHOLD",
                        target_entities=(info.entity_value,),
                    )
                )
                rec_counter += 1

        if overall_risk_level in ("HIGH", "CRITICAL"):
            recommendations.append(
                InvestigationRecommendation(
                    recommendation_id=f"REC-{rec_counter:03d}",
                    action="Escalate to Advanced Fraud Unit",
                    priority="HIGH",
                    reason=f"Investigation target reached {overall_risk_level} risk threshold.",
                    trigger="HIGH_SEVERITY_EVIDENCE",
                    target_entities=(target_value,),
                )
            )
            rec_counter += 1

        if not recommendations:
            recommendations.append(
                InvestigationRecommendation(
                    recommendation_id="REC-001",
                    action="Maintain Standard System Monitoring",
                    priority="LOW",
                    reason="No high-severity risk threshold breached during analysis.",
                    trigger="STANDARD_MONITORING",
                    target_entities=(target_value,),
                )
            )

        return recommendations

    def _build_data_quality(
        self,
        events: list[TimelineEvent],
        entity_info: list[EntityTimelineInfo],
        statistics: TimelineStatistics | None,
        fraud_evolution: list[FraudEvolutionEvent],
    ) -> InvestigationDataQuality:
        """Construct deterministic data quality metrics."""
        missing_data: list[str] = []
        isolated_entities: list[str] = []
        timeline_gaps: list[str] = []
        duplicate_entities: list[str] = []

        # 1. Missing Data
        for ev in events:
            if not ev.timestamp:
                missing_data.append(f"Event missing timestamp: '{ev.title}'")

        for info in entity_info:
            if not info.first_seen_complaint:
                missing_data.append(f"Entity missing first seen complaint: '{info.entity_value}'")

        # 2. Isolated Entities (entities appearing in only 1 complaint)
        for info in entity_info:
            if info.usage_count <= 1:
                isolated_entities.append(info.entity_value)

        # 3. Timeline Gaps (> 30 days gap between consecutive events)
        sorted_events = sorted([ev for ev in events if ev.timestamp], key=lambda x: x.timestamp)
        for i in range(len(sorted_events) - 1):
            t1 = sorted_events[i].timestamp
            t2 = sorted_events[i + 1].timestamp
            gap_days = (t2 - t1).days
            if gap_days > 30:
                timeline_gaps.append(
                    f"Timeline gap of {gap_days} days between '{sorted_events[i].title}' and '{sorted_events[i+1].title}'"
                )

        # 4. Duplicate Entities (same lookup value with different casing)
        seen_values: dict[str, str] = {}
        for info in entity_info:
            lower_val = info.entity_value.strip().lower()
            if lower_val in seen_values and seen_values[lower_val] != info.entity_value:
                duplicate_entities.append(f"Potential casing duplicate: '{info.entity_value}' vs '{seen_values[lower_val]}'")
            else:
                seen_values[lower_val] = info.entity_value

        # 5. Overall Data Quality Assessment
        if len(missing_data) > 2 or len(timeline_gaps) > 2:
            overall_quality = "LOW"
        elif len(missing_data) > 0 or len(timeline_gaps) > 0 or len(isolated_entities) > 5:
            overall_quality = "MEDIUM"
        else:
            overall_quality = "HIGH"

        return InvestigationDataQuality(
            missing_data=tuple(missing_data),
            isolated_entities=tuple(isolated_entities),
            timeline_gaps=tuple(timeline_gaps),
            duplicate_entities=tuple(duplicate_entities),
            overall_data_quality=overall_quality,
        )
