"""
Timeline Analysis Service.

Computes deterministic investigation statistics, duration analytics,
and rule-based insights without using AI or external models.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.schemas.timeline import (
    EntityTimelineInfo,
    InsightSeverity,
    TimelineEvent,
    TimelineInsight,
    TimelineStatistics,
)


class TimelineAnalysisService:
    """
    Service responsible for computing timeline statistics and deterministic insights.
    """

    def compute_statistics(
        self,
        raw_stats: dict[str, int],
    ) -> TimelineStatistics:
        """
        Build TimelineStatistics model from raw graph count dictionary.

        Args:
            raw_stats:
                Dictionary containing raw node counts from GraphRepository.

        Returns:
            TimelineStatistics model.
        """
        if not isinstance(raw_stats, dict):
            raw_stats = {}

        phones = raw_stats.get("phones", 0)

        upis = raw_stats.get("upis", 0)
        emails = raw_stats.get("emails", 0)
        urls = raw_stats.get("urls", 0)
        bank_accounts = raw_stats.get("bank_accounts", 0)
        organizations = raw_stats.get("organizations", 0)
        people = raw_stats.get("people", 0)
        locations = raw_stats.get("locations", 0)

        total_entities = (
            phones
            + upis
            + emails
            + urls
            + bank_accounts
            + organizations
            + people
            + locations
        )

        return TimelineStatistics(
            total_complaints=raw_stats.get("complaints", 0),
            total_entities=total_entities,
            phones=phones,
            upis=upis,
            emails=emails,
            urls=urls,
            bank_accounts=bank_accounts,
            organizations=organizations,
            people=people,
            locations=locations,
        )

    def compute_insights(
        self,
        events: list[TimelineEvent],
        entity_info: list[EntityTimelineInfo],
        statistics: TimelineStatistics,
    ) -> list[TimelineInsight]:
        """
        Compute deterministic rule-based timeline insights.

        Args:
            events:
                Chronological list of timeline events.
            entity_info:
                Chronological list of entity first appearances and usage metrics.
            statistics:
                Investigation statistics summary.

        Returns:
            List of TimelineInsight models.
        """
        logger.info(
            "Computing deterministic timeline insights for target network.",
        )

        insights: list[TimelineInsight] = []

        # Rule 1: Entity reuse detection with threshold-based severity
        for info in entity_info:
            if info.usage_count >= 3:
                entity_label = info.entity_type
                if entity_label.lower() == "phone":
                    desc = f"Phone number reused across {info.usage_count} complaints."
                elif entity_label.lower() in ("upi", "upi_id"):
                    desc = f"UPI ID '{info.entity_value}' reused across {info.usage_count} complaints."
                elif entity_label.lower() == "email":
                    desc = f"Email '{info.entity_value}' reused across {info.usage_count} complaints."
                elif entity_label.lower() == "bankaccount":
                    desc = f"Bank account '{info.entity_value}' reused across {info.usage_count} complaints."
                else:
                    desc = f"{entity_label} '{info.entity_value}' reused across {info.usage_count} complaints."

                severity = (
                    InsightSeverity.HIGH
                    if info.usage_count >= 5
                    else InsightSeverity.MEDIUM
                )

                insights.append(
                    TimelineInsight(
                        title="Entity Reuse Detected",
                        description=desc,
                        severity=severity,
                    )
                )


        # Rule 2: Timeline duration / multi-day activity
        if len(events) >= 2:
            start_ts = events[0].timestamp
            end_ts = events[-1].timestamp
            duration_days = (end_ts - start_ts).days
            if duration_days >= 1:
                insights.append(
                    TimelineInsight(
                        title="Extended Activity Duration",
                        description=f"Fraud activity persisted over {duration_days} days.",
                        severity=(
                            InsightSeverity.HIGH
                            if duration_days >= 7
                            else InsightSeverity.MEDIUM
                        ),
                    )
                )

        # Rule 3: Multiple phone numbers participated
        if statistics.phones > 1:
            insights.append(
                TimelineInsight(
                    title="Multiple Phone Numbers Detected",
                    description="Multiple phone numbers participated in the investigation.",
                    severity=InsightSeverity.MEDIUM,
                )
            )

        # Rule 4: Multiple payment identifiers
        if statistics.upis > 1:
            insights.append(
                TimelineInsight(
                    title="Multiple Payment Identifiers",
                    description="Multiple payment identifiers detected.",
                    severity=InsightSeverity.MEDIUM,
                )
            )

        logger.info("Generated {} deterministic insights.", len(insights))
        return insights
