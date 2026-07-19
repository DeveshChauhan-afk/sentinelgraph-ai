"""
Prompt context models for Graph-RAG.
"""

from __future__ import annotations

from pydantic import BaseModel


class PromptContext(BaseModel):
    """
    Structured context supplied to the LLM.
    """

    target: dict

    risk: dict

    neighbors: list[dict]

    related_incidents: list[dict]

    fraud_ring: dict

    shared_entities: list[dict]
