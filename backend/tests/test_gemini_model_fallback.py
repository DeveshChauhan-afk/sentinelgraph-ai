"""
Comprehensive unit and integration tests for Gemini Model Fallback.

Tests:
1. GEMINI_FALLBACK_MODELS configuration parsing (comma-delimited, JSON, defaults).
2. Ordered, deduplicated candidate model resolution.
3. Availability error classification (404, 429, 5xx, UNAVAILABLE, etc. vs 400, 401, 403, bugs).
4. Preservation of same-model retry/backoff behavior prior to fallback.
5. Fast fallback on 404 without wasteful same-model retries.
6. Fail-fast on non-availability errors (400, 401, 403, validation).
7. Chained multi-model fallback.
8. Preservation of response_schema in both generate() and generate_content().
9. Observability: exact per-attempt Prometheus labels and winning model in LLMMetadata.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch
import pytest
from google.genai.errors import ClientError, ServerError
from pydantic import BaseModel, Field, SecretStr

from app.ai.client import GeminiClient
from app.ai.exceptions import (
    AIAuthenticationError,
)
from app.core.config import Settings
from app.core.metrics import (
    llm_request_duration_seconds,
    llm_requests_total,
)
from app.exceptions.investigation import LLMProviderError
from app.schemas.llm_response import LLMResponse
from app.schemas.prompt import (
    DeveloperInstructions,
    ExpectedReportSection,
    ExpectedReportStructure,
    PromptConstraints,
    PromptMetadata,
    PromptRequest,
    SerializedContext,
    SystemPrompt,
)


def _build_fallback_settings(
    primary_model: str = "gemini-3.6-flash",
    fallback_models: list[str] | str | None = None,
    max_retries: int = 3,
    initial_delay: float = 0.001,
    max_delay: float = 0.005,
) -> Settings:
    """Helper to instantiate Settings with custom fallback configuration."""
    if fallback_models is None:
        fallback_models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]

    return Settings(
        SECRET_KEY=SecretStr("test-secret-key-01234567890123456789012345678901"),
        DATABASE_HOST="localhost",
        DATABASE_NAME="test_db",
        DATABASE_USER="test_user",
        DATABASE_PASSWORD=SecretStr("test_pass"),
        NEO4J_URI="bolt://localhost:7687",
        NEO4J_USERNAME="neo4j",
        NEO4J_PASSWORD=SecretStr("neo4j_pass"),
        GEMINI_API_KEY=SecretStr("test-gemini-key"),
        GEMINI_MODEL=primary_model,
        GEMINI_FALLBACK_MODELS=fallback_models,
        GEMINI_TIMEOUT_SECONDS=10.0,
        GEMINI_MAX_RETRIES=max_retries,
        GEMINI_RETRY_INITIAL_DELAY=initial_delay,
        GEMINI_RETRY_MAX_DELAY=max_delay,
    )


def _build_test_prompt_request(model_name: str | None = None) -> PromptRequest:
    """Helper to build a valid PromptRequest."""
    return PromptRequest(
        metadata=PromptMetadata(
            prompt_hash="f" * 64,
            model_name=model_name or "gemini-3.6-flash",
        ),
        system_prompt=SystemPrompt(role="Role", operating_rules=("Rule 1",)),
        developer_instructions=DeveloperInstructions(
            citation_instructions=("Cite 1",),
            style_guidelines=("Style 1",),
        ),
        context=SerializedContext(json_data='{"test": 1}', size_bytes=10),
        expected_structure=ExpectedReportStructure(
            sections=(
                ExpectedReportSection(
                    section_id="S1", title="Title 1", description="Desc 1"
                ),
            )
        ),
        constraints=PromptConstraints(),
    )


class DummySchema(BaseModel):
    summary: str = Field(default="test summary")


# ============================================================================
# 1. Configuration & Resolution Tests
# ============================================================================


def test_fallback_models_config_parsing() -> None:
    """Verify GEMINI_FALLBACK_MODELS parses strings, lists, JSON, and defaults."""
    # Default is empty list if not provided
    s_default = Settings(
        _env_file=None,
        SECRET_KEY=SecretStr("test-key-01234567890123456789012345678901"),
        DATABASE_HOST="localhost",
        DATABASE_NAME="db",
        DATABASE_USER="user",
        DATABASE_PASSWORD=SecretStr("pass"),
        NEO4J_URI="bolt://localhost:7687",
        NEO4J_USERNAME="neo4j",
        NEO4J_PASSWORD=SecretStr("pass"),
        GEMINI_API_KEY=SecretStr("key"),
    )
    assert s_default.GEMINI_FALLBACK_MODELS == []

    # Comma-separated string
    s_csv = _build_fallback_settings(
        fallback_models="gemini-2.5-flash, gemini-2.5-flash-lite "
    )
    assert s_csv.GEMINI_FALLBACK_MODELS == ["gemini-2.5-flash", "gemini-2.5-flash-lite"]

    # JSON array string
    s_json = _build_fallback_settings(
        fallback_models='["gemini-2.5-flash", "gemini-2.5-flash-lite"]'
    )
    assert s_json.GEMINI_FALLBACK_MODELS == [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    ]

    # Whitespace and empty elements
    s_dirty = _build_fallback_settings(
        fallback_models=" , gemini-2.5-flash , , gemini-2.5-flash-lite, "
    )
    assert s_dirty.GEMINI_FALLBACK_MODELS == [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    ]


def test_resolve_candidate_models_ordering_and_deduplication() -> None:
    """Verify candidate model list preserves order and removes duplicates."""
    settings = _build_fallback_settings(
        primary_model="gemini-3.6-flash",
        fallback_models=[
            "gemini-2.5-flash",
            "gemini-3.6-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
        ],
    )
    client = GeminiClient(settings)

    candidates = client._resolve_candidate_models()
    assert candidates == [
        "gemini-3.6-flash",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    ]

    # Preferred model override
    candidates_override = client._resolve_candidate_models(
        preferred_model="custom-gemini-model"
    )
    assert candidates_override == [
        "custom-gemini-model",
        "gemini-2.5-flash",
        "gemini-3.6-flash",
        "gemini-2.5-flash-lite",
    ]


# ============================================================================
# 2. Availability Error Classification Tests
# ============================================================================


def test_is_fallback_error_classification() -> None:
    """Verify that only availability/server errors trigger fallback."""
    settings = _build_fallback_settings()
    client = GeminiClient(settings)

    # Eligible availability errors
    assert (
        client._is_fallback_error(
            ClientError(404, {"error": {"message": "Model not found"}})
        )
        is True
    )
    assert (
        client._is_fallback_error(
            ClientError(429, {"error": {"message": "Resource exhausted"}})
        )
        is True
    )
    assert (
        client._is_fallback_error(
            ServerError(500, {"error": {"message": "Internal error"}})
        )
        is True
    )
    assert (
        client._is_fallback_error(
            ServerError(502, {"error": {"message": "Bad gateway"}})
        )
        is True
    )
    assert (
        client._is_fallback_error(
            ServerError(503, {"error": {"message": "Unavailable"}})
        )
        is True
    )
    assert (
        client._is_fallback_error(
            ServerError(504, {"error": {"message": "Gateway timeout"}})
        )
        is True
    )
    assert client._is_fallback_error(ConnectionResetError("Socket reset")) is True
    assert (
        client._is_fallback_error(ConnectionRefusedError("Connection refused")) is True
    )

    # gRPC / status string inspection
    status_exc = Exception("Custom provider failure")
    status_exc.status = "RESOURCE_EXHAUSTED"
    assert client._is_fallback_error(status_exc) is True
    status_exc2 = Exception("Provider is UNAVAILABLE")
    assert client._is_fallback_error(status_exc2) is True

    # Ineligible errors (MUST NOT trigger fallback)
    assert (
        client._is_fallback_error(
            ClientError(400, {"error": {"message": "Bad request"}})
        )
        is False
    )
    assert (
        client._is_fallback_error(
            ClientError(401, {"error": {"message": "Invalid API key"}})
        )
        is False
    )
    assert (
        client._is_fallback_error(ClientError(403, {"error": {"message": "Forbidden"}}))
        is False
    )
    assert client._is_fallback_error(AIAuthenticationError("Auth failed")) is False
    assert client._is_fallback_error(TypeError("Local code bug")) is False
    assert client._is_fallback_error(ValueError("Invalid argument")) is False
    assert client._is_fallback_error(asyncio.TimeoutError()) is False


# ============================================================================
# 3. Fallback Execution Tests
# ============================================================================


@pytest.mark.asyncio
async def test_primary_model_success_does_not_fallback() -> None:
    """When the primary model succeeds, fallback models are never invoked."""
    settings = _build_fallback_settings()
    client = GeminiClient(settings)

    mock_resp = MagicMock()
    mock_resp.text = '{"report_id": "RPT-1", "executive_summary": {}}'
    mock_resp.usage_metadata = MagicMock(
        prompt_token_count=10, candidates_token_count=20, total_token_count=30
    )
    mock_resp.candidates = [MagicMock(finish_reason="STOP")]

    client._client.models.generate_content = MagicMock(return_value=mock_resp)

    prompt = _build_test_prompt_request()
    res = await client.generate(prompt)

    assert isinstance(res, LLMResponse)
    assert res.metadata.model == "gemini-3.6-flash"
    assert client._client.models.generate_content.call_count == 1
    # Verify primary model was passed
    assert (
        client._client.models.generate_content.call_args.kwargs["model"]
        == "gemini-3.6-flash"
    )


@pytest.mark.asyncio
async def test_fallback_on_404_fast_fails_primary_without_retries() -> None:
    """
    HTTP 404 (model not found) on primary model must NOT waste 3 retries,
    but immediately fall back to the next candidate model.
    """
    settings = _build_fallback_settings(max_retries=3)
    client = GeminiClient(settings)

    err_404 = ClientError(
        404, {"error": {"message": "models/gemini-3.6-flash is not found"}}
    )
    mock_resp = MagicMock()
    mock_resp.text = '{"report_id": "RPT-2", "executive_summary": {}}'
    mock_resp.usage_metadata = None
    mock_resp.candidates = [MagicMock(finish_reason="STOP")]

    client._client.models.generate_content = MagicMock(side_effect=[err_404, mock_resp])

    prompt = _build_test_prompt_request()
    res = await client.generate(prompt)

    assert isinstance(res, LLMResponse)
    assert res.metadata.model == "gemini-2.5-flash"
    # Exactly 2 calls: 1 on primary (failed immediately without retry) + 1 on fallback (succeeded)
    assert client._client.models.generate_content.call_count == 2
    calls = client._client.models.generate_content.call_args_list
    assert calls[0].kwargs["model"] == "gemini-3.6-flash"
    assert calls[1].kwargs["model"] == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_fallback_on_429_exhausts_retries_on_primary_first() -> None:
    """
    HTTP 429 on primary model must retry up to max_retries before falling back.
    """
    settings = _build_fallback_settings(max_retries=3, initial_delay=0.001)
    client = GeminiClient(settings)

    err_429 = ClientError(429, {"error": {"message": "Resource exhausted"}})
    mock_resp = MagicMock()
    mock_resp.text = '{"report_id": "RPT-3", "executive_summary": {}}'
    mock_resp.usage_metadata = None
    mock_resp.candidates = [MagicMock(finish_reason="STOP")]

    # 3 attempts on primary (all 429), then 1 attempt on fallback (success)
    client._client.models.generate_content = MagicMock(
        side_effect=[err_429, err_429, err_429, mock_resp]
    )

    prompt = _build_test_prompt_request()
    res = await client.generate(prompt)

    assert res.metadata.model == "gemini-2.5-flash"
    assert client._client.models.generate_content.call_count == 4
    calls = client._client.models.generate_content.call_args_list
    assert calls[0].kwargs["model"] == "gemini-3.6-flash"
    assert calls[1].kwargs["model"] == "gemini-3.6-flash"
    assert calls[2].kwargs["model"] == "gemini-3.6-flash"
    assert calls[3].kwargs["model"] == "gemini-2.5-flash"


@pytest.mark.asyncio
async def test_chained_fallback_to_second_fallback_model() -> None:
    """
    When primary fails with 503 and fallback 1 fails with 404,
    fallback 2 is invoked and succeeds.
    """
    settings = _build_fallback_settings(
        primary_model="gemini-3.6-flash",
        fallback_models=["gemini-2.5-flash", "gemini-2.5-flash-lite"],
        max_retries=2,
    )
    client = GeminiClient(settings)

    err_503 = ServerError(503, {"error": {"message": "Unavailable"}})
    err_404 = ClientError(404, {"error": {"message": "Not found"}})
    mock_resp = MagicMock()
    mock_resp.text = '{"report_id": "RPT-CHAIN", "executive_summary": {}}'
    mock_resp.usage_metadata = None
    mock_resp.candidates = [MagicMock(finish_reason="STOP")]

    # Primary: 2x 503 -> Fallback 1: 1x 404 -> Fallback 2: 1x success
    client._client.models.generate_content = MagicMock(
        side_effect=[err_503, err_503, err_404, mock_resp]
    )

    prompt = _build_test_prompt_request()
    res = await client.generate(prompt)

    assert res.metadata.model == "gemini-2.5-flash-lite"
    assert client._client.models.generate_content.call_count == 4
    calls = client._client.models.generate_content.call_args_list
    assert calls[0].kwargs["model"] == "gemini-3.6-flash"
    assert calls[1].kwargs["model"] == "gemini-3.6-flash"
    assert calls[2].kwargs["model"] == "gemini-2.5-flash"
    assert calls[3].kwargs["model"] == "gemini-2.5-flash-lite"


@pytest.mark.asyncio
async def test_no_fallback_on_401_authentication_failure() -> None:
    """
    HTTP 401 must fail immediately on attempt 1 without attempting fallback models.
    """
    settings = _build_fallback_settings(fallback_models=["gemini-2.5-flash"])
    client = GeminiClient(settings)

    err_401 = ClientError(401, {"error": {"message": "API key invalid"}})
    client._client.models.generate_content = MagicMock(side_effect=err_401)

    prompt = _build_test_prompt_request()
    with pytest.raises(LLMProviderError) as exc_info:
        await client.generate(prompt)

    assert "401" in str(exc_info.value)
    # Exactly 1 call was made; no fallback was attempted
    assert client._client.models.generate_content.call_count == 1
    assert (
        client._client.models.generate_content.call_args.kwargs["model"]
        == "gemini-3.6-flash"
    )


@pytest.mark.asyncio
async def test_no_fallback_on_400_bad_request() -> None:
    """
    HTTP 400 must fail immediately without falling back to secondary models.
    """
    settings = _build_fallback_settings(fallback_models=["gemini-2.5-flash"])
    client = GeminiClient(settings)

    err_400 = ClientError(400, {"error": {"message": "Invalid argument"}})
    client._client.models.generate_content = MagicMock(side_effect=err_400)

    prompt = _build_test_prompt_request()
    with pytest.raises(LLMProviderError) as exc_info:
        await client.generate(prompt)

    assert "400" in str(exc_info.value)
    assert client._client.models.generate_content.call_count == 1


@pytest.mark.asyncio
async def test_all_models_exhausted_raises_error() -> None:
    """
    When all candidate models fail on availability errors, the final error is raised.
    """
    settings = _build_fallback_settings(
        primary_model="gemini-3.6-flash",
        fallback_models=["gemini-2.5-flash"],
        max_retries=1,
    )
    client = GeminiClient(settings)

    err_503_primary = ServerError(503, {"error": {"message": "Primary down"}})
    err_503_fallback = ServerError(503, {"error": {"message": "Fallback down"}})

    client._client.models.generate_content = MagicMock(
        side_effect=[err_503_primary, err_503_fallback]
    )

    prompt = _build_test_prompt_request()
    with pytest.raises(LLMProviderError):
        await client.generate(prompt)

    assert client._client.models.generate_content.call_count == 2


# ============================================================================
# 4. generate_content() and Structured Output Compatibility Tests
# ============================================================================


@pytest.mark.asyncio
async def test_generate_content_applies_fallback_and_preserves_schema() -> None:
    """
    generate_content() applies model fallback and passes the response_schema
    identically to the fallback model.
    """
    settings = _build_fallback_settings(max_retries=1)
    client = GeminiClient(settings)

    err_404 = ClientError(404, {"error": {"message": "Model decommissioned"}})
    mock_resp = MagicMock()
    mock_resp.text = '{"summary": "Fallback schema output"}'

    client._client.models.generate_content = MagicMock(side_effect=[err_404, mock_resp])

    result = await client.generate_content(
        "Extract summary", response_schema=DummySchema
    )

    assert result == '{"summary": "Fallback schema output"}'
    assert client._client.models.generate_content.call_count == 2

    # Verify both attempts preserved the response_schema
    calls = client._client.models.generate_content.call_args_list
    assert calls[0].kwargs["model"] == "gemini-3.6-flash"
    assert calls[0].kwargs["config"].response_schema == DummySchema
    assert calls[1].kwargs["model"] == "gemini-2.5-flash"
    assert calls[1].kwargs["config"].response_schema == DummySchema


@pytest.mark.asyncio
async def test_generate_content_legacy_translation_on_auth_failure() -> None:
    """
    generate_content() with HTTP 401 raises AIAuthenticationError without fallback.
    """
    settings = _build_fallback_settings(fallback_models=["gemini-2.5-flash"])
    client = GeminiClient(settings)

    err_401 = ClientError(401, {"error": {"message": "API key revoked"}})
    client._client.models.generate_content = MagicMock(side_effect=err_401)

    with pytest.raises(AIAuthenticationError):
        await client.generate_content("test prompt")

    assert client._client.models.generate_content.call_count == 1


# ============================================================================
# 5. Prometheus Observability Tests
# ============================================================================


@pytest.mark.asyncio
async def test_prometheus_metrics_record_exact_models_on_fallback() -> None:
    """
    Ensure that Prometheus request counter and duration metrics record the primary
    model as 'error' and fallback model as 'success'.
    """
    settings = _build_fallback_settings(max_retries=1)
    client = GeminiClient(settings)

    err_404 = ClientError(404, {"error": {"message": "Not found"}})
    mock_resp = MagicMock()
    mock_resp.text = '{"report_id": "RPT-PROM", "executive_summary": {}}'
    mock_resp.usage_metadata = None
    mock_resp.candidates = [MagicMock(finish_reason="STOP")]

    client._client.models.generate_content = MagicMock(side_effect=[err_404, mock_resp])

    with (
        patch.object(llm_requests_total, "labels") as mock_req_labels,
        patch.object(llm_request_duration_seconds, "labels") as mock_dur_labels,
    ):
        mock_req_counter = MagicMock()
        mock_req_labels.return_value = mock_req_counter
        mock_dur_hist = MagicMock()
        mock_dur_labels.return_value = mock_dur_hist

        prompt = _build_test_prompt_request()
        res = await client.generate(prompt)

        assert res.metadata.model == "gemini-2.5-flash"

        # Verify llm_requests_total labels
        req_calls = mock_req_labels.call_args_list
        assert any(
            c.kwargs.get("model") == "gemini-3.6-flash"
            and c.kwargs.get("status") == "error"
            for c in req_calls
        )
        assert any(
            c.kwargs.get("model") == "gemini-2.5-flash"
            and c.kwargs.get("status") == "success"
            for c in req_calls
        )

        # Verify duration observed for both models
        dur_calls = mock_dur_labels.call_args_list
        assert any(c.kwargs.get("model") == "gemini-3.6-flash" for c in dur_calls)
        assert any(c.kwargs.get("model") == "gemini-2.5-flash" for c in dur_calls)
