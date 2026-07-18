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

        neighbors = "\n".join(
            f"- {self._format_node(node)}"
            for node in evidence.neighbors.neighbors
        )

        incidents = "\n".join(
            f"- {self._format_node(node)}"
            for node in evidence.related_incidents.incidents
        )

        ring_nodes = "\n".join(
            f"- {self._format_node(node)}"
            for node in evidence.fraud_ring.nodes
        )

        shared = "\n".join(
            f"- {self._format_node(node)}"
            for node in evidence.shared_entities.complaints
        )

        reasons = "\n".join(
            f"- {reason}"
            for reason in evidence.risk.reasons
        )

        return f"""
You are an expert cybercrime investigator.

Your task is to analyze the fraud intelligence graph below.

==============================
TARGET ENTITY
==============================

{entity}

==============================
RISK ASSESSMENT
==============================

Risk Score: {evidence.risk.risk_score}
Risk Level: {evidence.risk.risk_level}

Reasons:

{reasons}

==============================
CONNECTED ENTITIES
==============================

{neighbors if neighbors else "None"}

==============================
RELATED COMPLAINTS
==============================

{incidents if incidents else "None"}

==============================
FRAUD RING
==============================

Total Nodes:
{evidence.fraud_ring.total_nodes}

Total Complaints:
{evidence.fraud_ring.total_incidents}

Members:

{ring_nodes if ring_nodes else "None"}

==============================
SHARED COMPLAINTS
==============================

{shared if shared else "None"}

==============================
INSTRUCTIONS
==============================

Generate a professional investigation report.

The report should contain:

1. Executive Summary

2. Risk Assessment

3. Fraud Ring Analysis

4. Key Evidence

5. Recommended Actions

6. Overall Conclusion

Only use the evidence provided above.

Do not fabricate any facts.

If evidence is insufficient, clearly state that.
""".strip()