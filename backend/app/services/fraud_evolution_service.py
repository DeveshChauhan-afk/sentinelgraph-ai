"""
Fraud Network Evolution Analysis Service.

Analyzes how an investigated fraud network evolves over time by detecting
network start, entity category introduction, infrastructure/communication expansion,
network expansion via complaints, and milestone thresholds.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from loguru import logger

from app.schemas.timeline import (
    EvolutionEventType,
    FraudEvolutionEvent,
    TimelineEvent,
)

# Configurable structural milestone thresholds
MILESTONE_THRESHOLDS: tuple[int, ...] = (5, 10, 20, 50, 100)


class FraudEvolutionService:
    """
    Service responsible for deterministic analysis of fraud network evolution.
    """

    def analyze_network_evolution(
        self,
        timeline_events: list[TimelineEvent],
        entity_occurrences: list[dict[str, Any]],
    ) -> list[FraudEvolutionEvent]:
        """
        Analyze timeline events and entity occurrences to construct evolution milestones.

        Args:
            timeline_events:
                Chronological list of timeline events (complaint creations, etc.).
            entity_occurrences:
                Raw entity occurrences across complaints.

        Returns:
            List of FraudEvolutionEvent models sorted chronologically by timestamp ascending.
        """
        logger.info(
            "Analyzing network evolution for {} timeline events and {} entity occurrences.",
            len(timeline_events),
            len(entity_occurrences),
        )

        if not timeline_events and not entity_occurrences:
            return []

        evolution_events: list[FraudEvolutionEvent] = []

        # 1. Standardize and organize complaints chronologically
        complaint_timestamps: dict[str, datetime] = {}
        complaint_entities: dict[str, list[dict[str, Any]]] = {}

        # Extract timestamps from timeline_events first
        for event in timeline_events:
            complaint_id = event.metadata.get("complaint_id")
            if complaint_id and event.timestamp:
                complaint_timestamps[str(complaint_id)] = event.timestamp

        # Extract timestamps and entity mapping from entity_occurrences
        for item in entity_occurrences:
            c_id = str(item.get("complaint_id", ""))
            if not c_id:
                continue

            created_at = item.get("created_at")
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                except ValueError:
                    created_at = None

            if c_id not in complaint_timestamps and isinstance(created_at, datetime):
                complaint_timestamps[c_id] = created_at

            if c_id not in complaint_entities:
                complaint_entities[c_id] = []
            complaint_entities[c_id].append(item)

        if not complaint_timestamps:
            return []

        # Sort complaints by timestamp ascending
        sorted_complaints = sorted(
            complaint_timestamps.items(),
            key=lambda x: x[1],
        )

        network_start_ts = sorted_complaints[0][1]
        first_complaint_id = sorted_complaints[0][0]

        # Rule 1: NETWORK_STARTED
        evolution_events.append(
            FraudEvolutionEvent(
                event_type=EvolutionEventType.NETWORK_STARTED,
                timestamp=network_start_ts,
                title="Fraud Network Started",
                description=(
                    f"Investigation begins with the first recorded complaint ({first_complaint_id})."
                ),
                related_complaints=[first_complaint_id],
                metadata={"complaint_id": first_complaint_id},
            )
        )

        # Track first appearance of each entity_type and entity lookup value
        entity_type_first_seen: dict[str, tuple[datetime, str, str]] = {}
        entity_value_first_seen: dict[tuple[str, str], tuple[datetime, str]] = {}

        for c_id, c_ts in sorted_complaints:
            items = complaint_entities.get(c_id, [])
            for item in items:
                e_type = item.get("entity_type")
                e_val = item.get("lookup_value")
                if not e_type or not e_val:
                    continue

                if e_type not in entity_type_first_seen:
                    entity_type_first_seen[e_type] = (c_ts, c_id, e_val)

                key = (e_type, e_val)
                if key not in entity_value_first_seen:
                    entity_value_first_seen[key] = (c_ts, c_id)

        # Rule 2: ENTITY_TYPE_INTRODUCED
        for e_type, (ts, c_id, e_val) in entity_type_first_seen.items():
            evolution_events.append(
                FraudEvolutionEvent(
                    event_type=EvolutionEventType.ENTITY_TYPE_INTRODUCED,
                    timestamp=ts,
                    title=f"{e_type} Entity Type Introduced",
                    description=f"{e_type} identifiers appeared for the first time.",
                    related_entities=[e_val],
                    related_complaints=[c_id],
                    metadata={"entity_type": e_type, "lookup_value": e_val},
                )
            )

        # Rule 3 & 4: Payment Infrastructure Expansion & Communication Channel Expansion
        payment_types = {"upi", "upi_id", "bankaccount", "bank_account"}
        comm_types = {"email", "url", "phone"}

        for (e_type, e_val), (ts, c_id) in entity_value_first_seen.items():
            # If appeared after network start
            if ts > network_start_ts:
                lower_type = e_type.lower()
                if lower_type in payment_types:
                    evolution_events.append(
                        FraudEvolutionEvent(
                            event_type=EvolutionEventType.PAYMENT_INFRASTRUCTURE_EXPANDED,
                            timestamp=ts,
                            title="Payment Infrastructure Expanded",
                            description=(
                                f"Payment infrastructure expanded with new {e_type} identifier '{e_val}'."
                            ),
                            related_entities=[e_val],
                            related_complaints=[c_id],
                            metadata={"entity_type": e_type, "lookup_value": e_val},
                        )
                    )
                elif lower_type in comm_types:
                    evolution_events.append(
                        FraudEvolutionEvent(
                            event_type=EvolutionEventType.COMMUNICATION_CHANNEL_EXPANDED,
                            timestamp=ts,
                            title="Communication Channel Expanded",
                            description=(
                                f"Communication channel expanded with new {e_type} identifier '{e_val}'."
                            ),
                            related_entities=[e_val],
                            related_complaints=[c_id],
                            metadata={"entity_type": e_type, "lookup_value": e_val},
                        )
                    )

        # Rule 5 & 6: NETWORK_EXPANDED and NETWORK_MILESTONE across complaints
        seen_entities: set[str] = set()

        for idx, (c_id, c_ts) in enumerate(sorted_complaints, start=1):
            items = complaint_entities.get(c_id, [])
            current_entities = {
                item.get("lookup_value")
                for item in items
                if item.get("lookup_value")
            }

            if seen_entities:
                newly_introduced = current_entities - seen_entities
                if newly_introduced:
                    evolution_events.append(
                        FraudEvolutionEvent(
                            event_type=EvolutionEventType.NETWORK_EXPANDED,
                            timestamp=c_ts,
                            title="Network Expanded",
                            description=(
                                f"Complaint {c_id} introduced {len(newly_introduced)} new entities into the network."
                            ),
                            related_entities=sorted(list(newly_introduced)),
                            related_complaints=[c_id],
                            metadata={
                                "complaint_id": c_id,
                                "newly_introduced_entities": sorted(list(newly_introduced)),
                            },
                        )
                    )

            seen_entities.update(current_entities)

            # Rule 6: Milestones
            if idx in MILESTONE_THRESHOLDS:
                evolution_events.append(
                    FraudEvolutionEvent(
                        event_type=EvolutionEventType.NETWORK_MILESTONE,
                        timestamp=c_ts,
                        title=f"Network Milestone: {idx} Complaints",
                        description=(
                            f"Fraud network reached a structural milestone of {idx} connected complaints."
                        ),
                        related_complaints=[c_id],
                        metadata={"milestone": idx, "complaint_count": idx},
                    )
                )

        # Deduplicate identical events if any and sort chronologically
        unique_events: list[FraudEvolutionEvent] = []
        seen_event_signatures: set[tuple[str, str, str]] = set()

        for ev in evolution_events:
            sig = (ev.event_type.value, ev.timestamp.isoformat(), ev.description)
            if sig not in seen_event_signatures:
                seen_event_signatures.add(sig)
                unique_events.append(ev)

        unique_events.sort(key=lambda x: x.timestamp)

        logger.info(
            "Constructed {} fraud network evolution events.",
            len(unique_events),
        )

        return unique_events
