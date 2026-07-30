"""
ReportContextBuilder Service Architecture (Sprint 9 Phase 2).

Transforms a deterministic canonical InvestigationSummary into an optimized, immutable
InvestigationReportContext specifically structured for LLM report consumption (PromptBuilder / Gemini).

Maintains strict Clean Architecture and SOLID principles:
- Contains NO persistence logic, database queries, or Neo4j queries.
- Contains NO LLM calls, natural language generation, or prompt engineering.
- Pure deterministic transformation preserving explainability, provenance, and citations.
"""

from __future__ import annotations

from loguru import logger

from app.schemas.investigation_report_context import (
    InvestigationReportContext,
    ReportCitationItem,
    ReportContextExecutiveStatistics,
    ReportContextMetadata,
    ReportContextOverview,
    ReportCriticalFinding,
    ReportEntityHighlight,
    ReportEntityHighlights,
    ReportEvolutionHighlights,
    ReportRecommendation,
    ReportSupportingEvidence,
    ReportTimelineHighlight,
    ReportTimelineHighlights,
)
from app.schemas.investigation_summary import InvestigationSummary
from app.schemas.timeline import EvidenceSeverity, EvolutionEventType, TimelineEvent


class ReportContextBuilder:
    """
    Service responsible for building token-optimized, report-oriented InvestigationReportContext
    view models from deterministic InvestigationSummary instances.
    """

    def build_report_context(
        self,
        summary: InvestigationSummary,
    ) -> InvestigationReportContext:
        """
        Transform a deterministic InvestigationSummary into an InvestigationReportContext.

        Args:
            summary: Source canonical InvestigationSummary DTO.

        Returns:
            Canonical immutable InvestigationReportContext DTO.
        """
        logger.info(
            "Building InvestigationReportContext for target '{}'.",
            summary.metadata.target_value,
        )

        metadata = self._build_metadata(summary)
        overview = self._build_overview(summary)
        exec_stats = self._build_statistics(summary)
        timeline_highlights = self._build_timeline_highlights(summary)
        entity_highlights = self._build_entity_highlights(summary)
        evolution_highlights = self._build_evolution_highlights(summary)
        critical_findings = self._build_findings(summary)
        recommendations = self._build_recommendations(summary)
        supporting_evidence = self._build_supporting_evidence(summary)
        citation_map = self._build_citation_map(summary)

        context = InvestigationReportContext(
            metadata=metadata,
            overview=overview,
            executive_statistics=exec_stats,
            timeline_highlights=timeline_highlights,
            entity_highlights=entity_highlights,
            evolution_highlights=evolution_highlights,
            critical_findings=critical_findings,
            recommendations=recommendations,
            supporting_evidence=supporting_evidence,
            citation_map=citation_map,
        )

        logger.info(
            "Successfully built InvestigationReportContext for target '{}': "
            "findings={}, recommendations={}, evidence={}, citations={}.",
            summary.metadata.target_value,
            len(critical_findings),
            len(recommendations),
            len(supporting_evidence),
            len(citation_map),
        )

        return context

    async def build_report_context_async(
        self,
        summary: InvestigationSummary,
    ) -> InvestigationReportContext:
        """
        Async wrapper for build_report_context to support async pipeline orchestration.
        """
        return self.build_report_context(summary)

    def _build_metadata(
        self,
        summary: InvestigationSummary,
    ) -> ReportContextMetadata:
        """Build ReportContextMetadata."""
        return ReportContextMetadata(
            report_context_version="1.0",
            generated_from_summary_version=summary.metadata.summary_version,
            generated_by="ReportContextBuilder",
        )

    def _build_overview(
        self,
        summary: InvestigationSummary,
    ) -> ReportContextOverview:
        """Build Executive Overview facts for report context."""
        return ReportContextOverview(
            target_value=summary.overview.target_value,
            target_type=summary.metadata.target_type,
            overall_risk_level=summary.overview.overall_risk_level,
            total_complaints=summary.overview.total_complaints,
            total_entities=summary.overview.total_entities,
            investigation_duration_days=summary.timeline.duration_days,
            time_range_start=summary.overview.time_range_start,
            time_range_end=summary.overview.time_range_end,
        )

    def _build_statistics(
        self,
        summary: InvestigationSummary,
    ) -> ReportContextExecutiveStatistics:
        """Build concise executive statistics without redundant metrics."""
        return ReportContextExecutiveStatistics(
            complaint_count=summary.statistics.total_complaints,
            entity_count=summary.statistics.total_entities,
            evidence_count=summary.evidence.total_evidence_units,
            reused_entity_count=summary.entities.reused_entities_count,
            fraud_ring_count=0,
            duration_days=summary.timeline.duration_days,
        )

    def _build_timeline_highlights(
        self,
        summary: InvestigationSummary,
    ) -> ReportTimelineHighlights:
        """Build compact executive timeline highlights filtering key milestone events."""
        events: list[TimelineEvent] = list(summary.timeline.events)
        if not events:
            return ReportTimelineHighlights(total_highlights=0, highlights=())

        sorted_events = sorted([e for e in events if e.timestamp], key=lambda x: x.timestamp)
        if not sorted_events:
            return ReportTimelineHighlights(total_highlights=0, highlights=())

        highlights: list[ReportTimelineHighlight] = []
        seen_signatures: set[tuple[str, str]] = set()

        def add_highlight(event: TimelineEvent, category: str):
            sig = (event.title, category)
            if sig not in seen_signatures:
                seen_signatures.add(sig)
                highlights.append(
                    ReportTimelineHighlight(
                        event_type=str(event.event_type.value if hasattr(event.event_type, "value") else event.event_type),
                        timestamp=event.timestamp,
                        title=event.title,
                        description=event.description or event.title,
                        category=category,
                    )
                )

        # 1. First observed activity
        add_highlight(sorted_events[0], "FIRST_OBSERVED")

        # 2. First payment entity event
        first_pay = next(
            (e for e in sorted_events if "payment" in e.title.lower() or "upi" in e.title.lower() or "account" in e.title.lower()),
            None,
        )
        if first_pay:
            add_highlight(first_pay, "FIRST_PAYMENT")

        # 3. First communication channel event
        first_comm = next(
            (e for e in sorted_events if "phone" in e.title.lower() or "email" in e.title.lower()),
            None,
        )
        if first_comm:
            add_highlight(first_comm, "FIRST_COMMUNICATION")

        # 4. Major expansion event
        first_expansion = next(
            (e for e in sorted_events if "expansion" in e.title.lower() or "milestone" in e.title.lower()),
            None,
        )
        if first_expansion:
            add_highlight(first_expansion, "MAJOR_EXPANSION")

        # 5. Latest observed activity
        add_highlight(sorted_events[-1], "LATEST_OBSERVED")

        # Ensure sorted chronologically by timestamp
        highlights.sort(key=lambda h: h.timestamp)

        return ReportTimelineHighlights(
            total_highlights=len(highlights),
            highlights=tuple(highlights),
        )

    def _build_entity_highlights(
        self,
        summary: InvestigationSummary,
    ) -> ReportEntityHighlights:
        """Select and rank high-value entities based on reuse and connections."""
        entities = list(summary.entities.entities)
        if not entities:
            return ReportEntityHighlights(total_highlights=0, highlights=())

        # Rank entities by usage count descending, then first seen ascending
        ranked = sorted(entities, key=lambda e: (-e.usage_count, e.first_seen))
        top_entities = ranked[:10]  # Take top 10 highest-value entities

        highlights: list[ReportEntityHighlight] = []
        for info in top_entities:
            e_type = info.entity_type.lower()
            if info.usage_count >= 2:
                if e_type in ("upi", "upi_id"):
                    reason = "HIGH_REUSE_UPI"
                elif e_type in ("bankaccount", "bank_account"):
                    reason = "HIGH_REUSE_BANK_ACCOUNT"
                elif e_type == "phone":
                    reason = "HIGH_REUSE_PHONE"
                elif e_type == "email":
                    reason = "NOTABLE_EMAIL"
                else:
                    reason = "HIGHLY_CONNECTED_ENTITY"
            else:
                reason = "NOTABLE_INVESTIGATION_ENTITY"

            highlights.append(
                ReportEntityHighlight(
                    entity_type=info.entity_type,
                    entity_value=info.entity_value,
                    usage_count=info.usage_count,
                    first_seen=info.first_seen,
                    complaint_ids=tuple(info.complaint_ids),
                    rank_reason=reason,
                )
            )

        return ReportEntityHighlights(
            total_highlights=len(highlights),
            highlights=tuple(highlights),
        )

    def _build_evolution_highlights(
        self,
        summary: InvestigationSummary,
    ) -> ReportEvolutionHighlights:
        """Summarize deterministic network evolution chronology."""
        events = list(summary.evolution.events)
        if not events:
            return ReportEvolutionHighlights(
                network_origin=None,
                payment_expansion=(),
                communication_expansion=(),
                network_growth=(),
                current_network_stage="INITIAL_STAGE",
            )

        origin_desc: str | None = None
        pay_exp: list[str] = []
        comm_exp: list[str] = []
        growth_exp: list[str] = []

        for ev in events:
            e_type = ev.event_type.value if hasattr(ev.event_type, "value") else str(ev.event_type)
            if e_type == "NETWORK_STARTED" and not origin_desc:
                origin_desc = ev.description
            elif e_type == "PAYMENT_INFRASTRUCTURE_EXPANDED":
                pay_exp.append(ev.description)
            elif e_type == "COMMUNICATION_CHANNEL_EXPANDED":
                comm_exp.append(ev.description)
            elif e_type in ("NETWORK_EXPANDED", "NETWORK_MILESTONE"):
                growth_exp.append(ev.description)

        complaints_cnt = summary.statistics.total_complaints
        reused_cnt = summary.entities.reused_entities_count

        if complaints_cnt >= 20:
            stage = "ESTABLISHED_COORDINATED_RING"
        elif complaints_cnt >= 5 or reused_cnt > 1:
            stage = "EXPANDING_FRAUD_NETWORK"
        else:
            stage = "INITIAL_EMERGING_STAGE"

        return ReportEvolutionHighlights(
            network_origin=origin_desc or (events[0].description if events else None),
            payment_expansion=tuple(pay_exp),
            communication_expansion=tuple(comm_exp),
            network_growth=tuple(growth_exp),
            current_network_stage=stage,
        )

    def _build_findings(
        self,
        summary: InvestigationSummary,
    ) -> tuple[ReportCriticalFinding, ...]:
        """Transform InvestigationFindings into report-ready findings with provenance."""
        report_findings: list[ReportCriticalFinding] = []

        for f in summary.findings:
            report_findings.append(
                ReportCriticalFinding(
                    finding_id=f.finding_id,
                    type=f.type,
                    severity=f.severity,
                    confidence=f.confidence,
                    title=f.title,
                    description=f.description,
                    supporting_complaint_ids=tuple(f.supporting_complaint_ids),
                    supporting_entity_ids=tuple(f.supporting_entity_ids),
                    supporting_evidence_ids=tuple(f.supporting_evidence_ids),
                )
            )

        return tuple(report_findings)

    def _build_recommendations(
        self,
        summary: InvestigationSummary,
    ) -> tuple[ReportRecommendation, ...]:
        """Transform recommendations into report-ready recommendations."""
        recs: list[ReportRecommendation] = []

        for r in summary.recommendations:
            recs.append(
                ReportRecommendation(
                    recommendation_id=r.recommendation_id,
                    action=r.action,
                    priority=r.priority,
                    reason=r.reason,
                    trigger=r.trigger,
                    affected_entities=tuple(r.target_entities),
                )
            )

        return tuple(recs)

    def _build_supporting_evidence(
        self,
        summary: InvestigationSummary,
    ) -> tuple[ReportSupportingEvidence, ...]:
        """Filter and include materially supporting evidence units."""
        all_evidence = list(summary.evidence.evidence_items)
        if not all_evidence:
            return ()

        # Prefer CRITICAL, HIGH, or confidence >= 0.75 evidence
        material_evidence = [
            e for e in all_evidence
            if (e.severity.value if hasattr(e.severity, "value") else str(e.severity).upper()) in ("CRITICAL", "HIGH")
            or e.confidence >= 0.75
        ]

        if not material_evidence:
            material_evidence = all_evidence

        # Sort by confidence descending
        material_evidence.sort(key=lambda x: x.confidence, reverse=True)

        report_ev: list[ReportSupportingEvidence] = []
        for e in material_evidence:
            report_ev.append(
                ReportSupportingEvidence(
                    evidence_id=str(e.evidence_id),
                    evidence_type=e.evidence_type.value if hasattr(e.evidence_type, "value") else str(e.evidence_type),
                    severity=e.severity.value if hasattr(e.severity, "value") else str(e.severity),
                    confidence=e.confidence,
                    title=e.title,
                    description=e.description,
                    supporting_entities=tuple(e.supporting_entities),
                    supporting_complaints=tuple(e.supporting_complaints),
                )
            )

        return tuple(report_ev)

    def _build_citation_map(
        self,
        summary: InvestigationSummary,
    ) -> tuple[ReportCitationItem, ...]:
        """Build structured citation index mapping findings to supporting evidence, complaints, entities."""
        citations: list[ReportCitationItem] = []

        for f in summary.findings:
            citations.append(
                ReportCitationItem(
                    finding_id=f.finding_id,
                    evidence_ids=tuple(f.supporting_evidence_ids),
                    complaint_ids=tuple(f.supporting_complaint_ids),
                    entity_ids=tuple(f.supporting_entity_ids),
                )
            )

        return tuple(citations)
