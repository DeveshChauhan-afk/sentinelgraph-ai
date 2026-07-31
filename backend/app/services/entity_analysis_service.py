#app/services/entity_analysis_service.py
"""
Entity Analysis Service for Timeline Reconstruction.

Analyzes entity occurrences across complaints to compute first appearance,
usage frequencies, and entity evolution chronologically.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from loguru import logger

from app.schemas.timeline import EntityTimelineInfo


class EntityAnalysisService:
    """
    Service responsible for entity evolution and appearance analysis.
    """

    def analyze_entities(
        self,
        entity_occurrences: list[dict[str, Any]],
    ) -> list[EntityTimelineInfo]:
        """
        Analyze entity occurrences and compute first appearance & usage metrics.

        Args:
            entity_occurrences:
                List of plain dictionaries with entity_type, lookup_value, complaint_id, created_at.

        Returns:
            List of EntityTimelineInfo models sorted by first_seen ascending.
        """
        logger.info(
            "Analyzing {} entity occurrences for timeline evolution.",
            len(entity_occurrences),
        )

        if not isinstance(entity_occurrences, list):
            entity_occurrences = []

        if not entity_occurrences:

            return []

        # Group occurrences by (entity_type, lookup_value)
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}

        for item in entity_occurrences:
            entity_type = item.get("entity_type") or "Unknown"
            lookup_value = item.get("lookup_value")
            if not lookup_value:
                continue

            key = (entity_type, lookup_value)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(item)

        results: list[EntityTimelineInfo] = []

        for (entity_type, lookup_value), items in grouped.items():
            # Parse created_at timestamps and find earliest
            parsed_items: list[tuple[datetime, str]] = []
            distinct_complaints: set[str] = set()

            for item in items:
                created_at = item.get("created_at")
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.fromisoformat(
                            created_at.replace("Z", "+00:00")
                        )
                    except ValueError:
                        continue
                elif not isinstance(created_at, datetime):
                    continue

                complaint_id = str(item.get("complaint_id", ""))
                distinct_complaints.add(complaint_id)
                parsed_items.append((created_at, complaint_id))

            if not parsed_items:
                continue

            # Sort items for this entity to find earliest appearance
            parsed_items.sort(key=lambda x: x[0])
            first_seen, first_seen_complaint = parsed_items[0]
            # Preserve complaint IDs ordered by appearance
            ordered_complaint_ids = list(dict.fromkeys([c_id for _, c_id in parsed_items if c_id]))
            usage_count = len(ordered_complaint_ids)

            results.append(
                EntityTimelineInfo(
                    entity_type=entity_type,
                    entity_value=lookup_value,
                    first_seen=first_seen,
                    first_seen_complaint=first_seen_complaint,
                    usage_count=usage_count,
                    complaint_ids=ordered_complaint_ids,
                )
            )


        # Sort all entity timeline infos by first_seen ascending
        results.sort(key=lambda info: info.first_seen)

        logger.info(
            "Completed entity evolution analysis for {} unique entities.",
            len(results),
        )

        return results
