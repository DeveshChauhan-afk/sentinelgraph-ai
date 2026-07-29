"""
Timeline Reconstruction Engine Orchestration Service.

Orchestrates GraphRepository, EntityAnalysisService, and TimelineAnalysisService
to construct complete investigation timelines with entity evolution, statistics,
and deterministic insights.
"""

from __future__ import annotations

from datetime import datetime

from loguru import logger

from app.graph.repository import GraphRepository
from app.schemas.timeline import (
    TimelineEvent,
    TimelineEventType,
    TimelineResponse,
    TimelineStatistics,
)
from app.services.entity_analysis_service import EntityAnalysisService
from app.services.evidence_engine import EvidenceEngine
from app.services.fraud_evolution_service import FraudEvolutionService
from app.services.timeline_analysis_service import TimelineAnalysisService


class TimelineService:
    """
    Orchestration service for building complete investigation timelines.
    """

    def __init__(
        self,
        repository: GraphRepository,
        entity_analysis_service: EntityAnalysisService | None = None,
        timeline_analysis_service: TimelineAnalysisService | None = None,
        fraud_evolution_service: FraudEvolutionService | None = None,
        evidence_engine: EvidenceEngine | None = None,
    ) -> None:
        """
        Initialize TimelineService.

        Args:
            repository:
                GraphRepository instance for accessing Neo4j persistence.
            entity_analysis_service:
                Optional EntityAnalysisService instance. Defaults to new instance if omitted.
            timeline_analysis_service:
                Optional TimelineAnalysisService instance. Defaults to new instance if omitted.
            fraud_evolution_service:
                Optional FraudEvolutionService instance. Defaults to new instance if omitted.
            evidence_engine:
                Optional EvidenceEngine instance. Defaults to new instance if omitted.
        """
        self._repository = repository
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

    async def build_timeline(
        self,
        entity_value: str,
    ) -> TimelineResponse:
        """
        Build a complete, chronological timeline with entity evolution, stats, insights, fraud evolution, and evidence.

        Args:
            entity_value:
                Entity or complaint lookup value to reconstruct a timeline for.

        Returns:
            TimelineResponse containing events, entity_first_seen, statistics, insights, fraud_evolution, and evidence.
        """
        logger.info(
            "Orchestrating timeline reconstruction for investigation target '{}'.",
            entity_value,
        )

        # 1. Retrieve connected complaints from GraphRepository
        complaints_data = await self._repository.get_connected_complaints(
            entity_value=entity_value,
        )

        if not complaints_data:
            logger.info(
                "No connected complaints found for target '{}'. Returning empty timeline response.",
                entity_value,
            )
            empty_stats = TimelineStatistics(
                total_complaints=0,
                total_entities=0,
                phones=0,
                upis=0,
                emails=0,
                urls=0,
                bank_accounts=0,
                organizations=0,
                people=0,
                locations=0,
            )
            return TimelineResponse(
                investigation_target=entity_value,
                total_events=0,
                start_time=None,
                end_time=None,
                events=[],
                entity_first_seen=[],
                statistics=empty_stats,
                insights=[],
                fraud_evolution=[],
                evidence=[],
            )

        # 2. Build chronological TimelineEvent objects
        events: list[TimelineEvent] = []
        seen_complaint_ids: set[str] = set()

        for item in complaints_data:
            complaint_id = item.get("complaint_id")
            if not complaint_id or complaint_id in seen_complaint_ids:
                continue

            seen_complaint_ids.add(complaint_id)

            created_at = item.get("created_at")
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            event = TimelineEvent(
                event_type=TimelineEventType.COMPLAINT_CREATED,
                timestamp=created_at,
                title=f"Complaint Created: {complaint_id}",
                description=(
                    f"Complaint {complaint_id} registered with lookup value "
                    f"'{item.get('lookup_value', complaint_id)}'"
                ),
                metadata={
                    "complaint_id": complaint_id,
                    "lookup_value": item.get("lookup_value", complaint_id),
                },
            )
            events.append(event)

        # Sort timeline events by timestamp ascending
        events.sort(key=lambda event: event.timestamp)

        total_events = len(events)
        start_time = events[0].timestamp if total_events > 0 else None
        end_time = events[-1].timestamp if total_events > 0 else None

        # 3. Retrieve entity occurrences and compute entity evolution
        entity_occurrences = await self._repository.get_entity_occurrences(
            entity_value=entity_value,
        )
        entity_first_seen = self._entity_analysis_service.analyze_entities(
            entity_occurrences=entity_occurrences,
        )

        # 4. Retrieve raw statistics and compute statistics summary
        raw_stats = await self._repository.get_timeline_statistics(
            entity_value=entity_value,
        )
        statistics = self._timeline_analysis_service.compute_statistics(
            raw_stats=raw_stats,
        )

        # 5. Compute deterministic insights
        insights = self._timeline_analysis_service.compute_insights(
            events=events,
            entity_info=entity_first_seen,
            statistics=statistics,
        )

        # 6. Compute fraud network evolution
        fraud_evolution = self._fraud_evolution_service.analyze_network_evolution(
            timeline_events=events,
            entity_occurrences=entity_occurrences,
        )

        # 7. Synthesize structured evidence
        evidence = self._evidence_engine.build_evidence(
            timeline_events=events,
            entity_info=entity_first_seen,
            timeline_statistics=statistics,
            timeline_insights=insights,
            fraud_evolution=fraud_evolution,
        )

        logger.info(
            "Completed timeline orchestration for '{}': events={}, entities={}, insights={}, evolution={}, evidence={}.",
            entity_value,
            total_events,
            len(entity_first_seen),
            len(insights),
            len(fraud_evolution),
            len(evidence),
        )

        return TimelineResponse(
            investigation_target=entity_value,
            total_events=total_events,
            start_time=start_time,
            end_time=end_time,
            events=events,
            entity_first_seen=entity_first_seen,
            statistics=statistics,
            insights=insights,
            fraud_evolution=fraud_evolution,
            evidence=evidence,
        )


