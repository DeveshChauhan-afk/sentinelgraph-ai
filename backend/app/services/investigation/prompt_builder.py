# app/service/investigation/prompt_builder
"""
Prompt builder for Graph-RAG investigations.
"""

from __future__ import annotations

from app.graph.models import GraphNode
from app.schemas.investigation import InvestigationEvidence


class PromptBuilder:
    """
    Builds structured prompts for the LLM from graph evidence.
    """

    @staticmethod
    def _format_node(node: GraphNode) -> str:
        """
        Convert a graph node into a readable string.
        """

        value = node.properties.get("value", "Unknown")

        return f"{node.label.value}: {value}"

    def build(
        self,
        evidence: InvestigationEvidence,
    ) -> str:
        """
        Build the Graph-RAG prompt.
        """

        entity = self._format_node(
            evidence.neighbors.entity,
        )

        neighbors = (
            "\n".join(
                f"- {self._format_node(node)}" for node in evidence.neighbors.neighbors
            )
            or "None"
        )

        incidents = (
            "\n".join(
                f"- {self._format_node(node)}"
                for node in evidence.related_incidents.incidents
            )
            or "None"
        )

        ring_members = (
            "\n".join(
                f"- {self._format_node(node)}" for node in evidence.fraud_ring.nodes
            )
            or "None"
        )

        shared = (
            "\n".join(
                f"- {self._format_node(node)}"
                for node in evidence.shared_entities.complaints
            )
            or "None"
        )

        reasons = "\n".join(f"- {reason}" for reason in evidence.risk.reasons) or "None"

        metrics = evidence.risk.metrics

        return f"""
    SYSTEM ROLE

    You are SentinelGraph AI.

    You are an expert cybercrime investigator specializing in:

    - Financial fraud
    - Digital arrest scams
    - UPI fraud
    - Identity theft
    - Fraud rings
    - Organized cybercrime

    You MUST base every conclusion exclusively on the supplied graph evidence.

    Never fabricate entities, complaints, relationships, dates, organizations, or risk factors that are not present in the evidence.

    You ONLY use the graph evidence provided.

    If evidence is insufficient, explicitly state that.

    ================================================

    GRAPH EVIDENCE

    ================================================

    Target Entity Under Investigation

    {entity}

    ------------------------------------------------

    Risk Assessment

    Risk Score: {evidence.risk.risk_score}

    Risk Level: {evidence.risk.risk_level}

    Reasons

    {reasons}

    Metrics

    - Complaint Count: {metrics.incident_count}
    - Neighbor Count: {metrics.neighbor_count}
    - Phone Count: {metrics.phone_count}
    - UPI Count: {metrics.upi_count}
    - Email Count: {metrics.email_count}
    - Organization Count: {metrics.organization_count}

    ------------------------------------------------

    Connected Entities

    {neighbors}

    ------------------------------------------------

    Related Complaints

    {incidents}

    ------------------------------------------------

    Fraud Ring

    Ring Size:
    {evidence.fraud_ring.total_nodes}

    Incident Count:
    {evidence.fraud_ring.total_incidents}

    Members

    {ring_members}

    ------------------------------------------------

    Shared Complaints

    {shared}

    ================================================

    TASK

    ================================================

    Analyze the graph evidence.

    Determine:

    • Assess the likelihood that the entity is associated with fraudulent activity based solely on the provided evidence.
    • Whether there is evidence of organized fraud.
    • Which graph connections contributed to the conclusion.
    • Whether investigators should prioritize this case.

    ================================================

    OUTPUT FORMAT

    ================================================

    Include a confidence score between 0 and 100 that reflects how strongly the supplied graph evidence supports your conclusions.
    Each item in key_evidence must reference specific evidence from the supplied graph, not opinions.
    Recommendations must be directly supported by the supplied evidence. Do not recommend actions based on assumptions or missing information.
    Return ONLY a valid JSON object.

    The JSON must contain exactly these fields:

    confidence
    executive_summary
    risk_assessment
    fraud_ring_analysis
    key_evidence
    recommended_actions
    overall_conclusion

    Do not output any text before or after the JSON.

    Do NOT include markdown.

    Do NOT include code fences.

    Do NOT include explanations outside the JSON.

    If the supplied evidence is weak or incomplete,
    state that clearly instead of making assumptions.
    """.strip()
