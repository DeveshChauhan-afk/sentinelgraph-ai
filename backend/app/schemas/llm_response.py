"""
Schemas for LLM Response and Execution Metadata (Sprint 9 Phase 4).

Provides immutable Pydantic models for LLMMetadata, LLMUsage, and LLMResponse.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class LLMMetadata(BaseModel):
    """
    Metadata for LLM execution request.
    """

    model_config = ConfigDict(frozen=True)

    provider: str = Field(
        ..., description="LLM Provider identifier (e.g. Gemini, OpenAI)."
    )
    model: str = Field(..., description="Model name used for generation.")
    request_id: str = Field(..., description="Unique request identifier.")
    latency_ms: float = Field(
        ..., ge=0.0, description="Execution latency in milliseconds."
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when completion was received.",
    )
    prompt_hash: str = Field(
        ..., description="SHA-256 fingerprint hash of input prompt."
    )


class LLMUsage(BaseModel):
    """
    Token usage metrics.
    """

    model_config = ConfigDict(frozen=True)

    prompt_tokens: int = Field(
        default=0, ge=0, description="Input prompt tokens."
    )
    completion_tokens: int = Field(
        default=0, ge=0, description="Generated completion tokens."
    )
    total_tokens: int = Field(
        default=0, ge=0, description="Total tokens consumed."
    )


class LLMResponse(BaseModel):
    """
    Canonical immutable response returned by LLMClient providers.
    """

    model_config = ConfigDict(frozen=True)

    metadata: LLMMetadata = Field(..., description="Execution metadata.")
    usage: LLMUsage = Field(..., description="Token usage statistics.")
    finish_reason: str = Field(
        default="STOP", description="Completion finish reason."
    )
    response_text: str = Field(
        ..., description="Raw text or JSON completion string."
    )
