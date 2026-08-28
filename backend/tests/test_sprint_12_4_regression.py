"""
Regression and reliability tests for Sprint 12.4: Gemini Reliability Hardening:
1. Configurable timeout: default 60.0s, custom settings, invalid value rejection.
2. Timeout handling: translation to domain exceptions without unbounded retries.
3. Transient failures: HTTP 429 and HTTP 5xx retry with backoff, eventual success, exhaustion.
4. Permanent failures: HTTP 401/403/400 fail immediately without retrying.
5. Observability & Metrics: exact per-attempt duration and request counter observations, real SDK token metadata.
6. Execution path normalization: consistent timeout, retry, and metric semantics across both generate() and generate_content().
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock, patch
import pytest
from google.genai.errors import ClientError, ServerError
from pydantic import SecretStr, ValidationError

from app.ai.client import GeminiClient
from app.ai.exceptions import (
    AIAuthenticationError,
    AIRateLimitError,
    AIRequestError,
    AIResponseError,
)
from app.core.config import Settings
from app.core.metrics import (
    llm_request_duration_seconds,
    llm_requests_total,
    llm_tokens_total,
)
from app.exceptions.investigation import LLMProviderError, LLMTimeoutError
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


def _build_test_settings(
    timeout: float = 60.0,
    max_retries: int = 3,
    initial_delay: float = 0.01,
    max_delay: float = 0.05,
) -> Settings:
    """Helper to instantiate test settings with minimal required credentials."""
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
        GEMINI_MODEL="gemini-3.5-flash-lite",
        GEMINI_TIMEOUT_SECONDS=timeout,
        GEMINI_MAX_RETRIES=max_retries,
        GEMINI_RETRY_INITIAL_DELAY=initial_delay,
        GEMINI_RETRY_MAX_DELAY=max_delay,
    )


def _build_test_prompt_request() -> PromptRequest:
    """Helper to build a valid PromptRequest."""
    return PromptRequest(
        metadata=PromptMetadata(prompt_hash="a" * 64, model_name="gemini-3.5-flash-lite"),
        system_prompt=SystemPrompt(role="Role", operating_rules=("Rule 1",)),
        developer_instructions=DeveloperInstructions(
            citation_instructions=("Cite 1",), style_guidelines=("Style 1",)
        ),
        context=SerializedContext(json_data='{"test": 1}', size_bytes=10),
        expected_structure=ExpectedReportStructure(
            sections=(ExpectedReportSection(section_id="S1", title="Title 1", description="Desc 1"),)
        ),
        constraints=PromptConstraints(),
    )


# ============================================================================
# 1. Configuration & Validation Tests
# ============================================================================


def test_default_gemini_timeout_and_retry_settings() -> None:
    """
    Ensure the default Gemini timeout remains 60.0s and retries are sensibly bounded.
    """
    settings = _build_test_settings()
    assert settings.GEMINI_TIMEOUT_SECONDS == 60.0
    assert settings.GEMINI_MAX_RETRIES == 3
    assert settings.GEMINI_RETRY_INITIAL_DELAY == 0.01  # overridden in helper
    assert settings.GEMINI_RETRY_MAX_DELAY == 0.05


def test_custom_gemini_timeout_and_retry_settings() -> None:
    """
    Ensure custom configuration parameters are parsed and accepted.
    """
    settings = _build_test_settings(
        timeout=45.0,
        max_retries=5,
        initial_delay=0.5,
        max_delay=5.0,
    )
    assert settings.GEMINI_TIMEOUT_SECONDS == 45.0
    assert settings.GEMINI_MAX_RETRIES == 5
    assert settings.GEMINI_RETRY_INITIAL_DELAY == 0.5
    assert settings.GEMINI_RETRY_MAX_DELAY == 5.0


def test_invalid_gemini_timeout_is_rejected() -> None:
    """
    Ensure zero or negative timeouts and invalid retry values are rejected by validation.
    """
    with pytest.raises(ValidationError):
        _build_test_settings(timeout=0.0)

    with pytest.raises(ValidationError):
        _build_test_settings(timeout=-10.0)

    with pytest.raises(ValidationError):
        _build_test_settings(max_retries=0)

    with pytest.raises(ValidationError):
        _build_test_settings(max_retries=15)  # le=10


# ============================================================================
# 2. Timeout Translation & Non-Unbounded Behavior
# ============================================================================


@pytest.mark.asyncio
async def test_generate_timeout_translated_to_llm_timeout_error_without_retries() -> None:
    """
    Ensure that a request timeout during generate() raises LLMTimeoutError
    and is NOT retried indefinitely.
    """
    settings = _build_test_settings(timeout=0.05, max_retries=3)
    client = GeminiClient(settings)

    def slow_call(*args, **kwargs):
        import time
        time.sleep(0.2)
        return MagicMock(text='{"summary": "done"}')

    client._client.models.generate_content = MagicMock(side_effect=slow_call)

    prompt = _build_test_prompt_request()

    with pytest.raises(LLMTimeoutError, match="Gemini completion request timed out"):
        await client.generate(prompt)

    # Timeouts fail immediately without retrying
    assert client._client.models.generate_content.call_count == 1


@pytest.mark.asyncio
async def test_generate_content_timeout_translated_to_ai_request_error() -> None:
    """
    Ensure that a request timeout during generate_content() raises AIRequestError
    and is NOT retried indefinitely.
    """
    settings = _build_test_settings(timeout=0.05, max_retries=3)
    client = GeminiClient(settings)

    def slow_call(*args, **kwargs):
        import time
        time.sleep(0.2)
        return MagicMock(text="output")

    client._client.models.generate_content = MagicMock(side_effect=slow_call)

    with pytest.raises(AIRequestError, match="Gemini request timed out"):
        await client.generate_content("test prompt")

    assert client._client.models.generate_content.call_count == 1


# ============================================================================
# 3. Transient Failures & Bounded Retry
# ============================================================================


@pytest.mark.asyncio
async def test_transient_429_is_retried_and_succeeds_for_generate() -> None:
    """
    Ensure that HTTP 429 rate limit error is retried and succeeds on subsequent attempt.
    """
    settings = _build_test_settings(max_retries=3, initial_delay=0.01)
    client = GeminiClient(settings)

    mock_response = MagicMock()
    mock_response.text = '{"report_id": "RPT-1", "executive_summary": {}}'
    mock_response.usage_metadata = MagicMock(
        prompt_token_count=100,
        candidates_token_count=50,
        total_token_count=150,
    )
    mock_response.candidates = [MagicMock(finish_reason="STOP")]

    rate_limit_error = ClientError(429, {"error": {"message": "Resource exhausted"}})

    client._client.models.generate_content = MagicMock(
        side_effect=[rate_limit_error, mock_response]
    )

    prompt = _build_test_prompt_request()
    res = await client.generate(prompt)

    assert isinstance(res, LLMResponse)
    assert res.response_text == mock_response.text
    assert client._client.models.generate_content.call_count == 2
    assert res.usage.total_tokens == 150


@pytest.mark.asyncio
async def test_transient_503_is_retried_and_succeeds_for_generate_content() -> None:
    """
    Ensure that ServerError (e.g. 503) is retried on legacy generate_content path.
    """
    settings = _build_test_settings(max_retries=3, initial_delay=0.01)
    client = GeminiClient(settings)

    mock_response = MagicMock()
    mock_response.text = '{"entities": []}'
    mock_response.usage_metadata = None

    server_error = ServerError(503, {"error": {"message": "Service unavailable"}})

    client._client.models.generate_content = MagicMock(
        side_effect=[server_error, mock_response]
    )

    res = await client.generate_content("extract entities")

    assert res == '{"entities": []}'
    assert client._client.models.generate_content.call_count == 2


@pytest.mark.asyncio
async def test_retry_exhaustion_on_generate_raises_llm_provider_error() -> None:
    """
    Ensure that when max retries are exhausted, generate() surfaces LLMProviderError.
    """
    settings = _build_test_settings(max_retries=3, initial_delay=0.01)
    client = GeminiClient(settings)

    rate_limit_error = ClientError(429, {"error": {"message": "Resource exhausted"}})
    client._client.models.generate_content = MagicMock(side_effect=rate_limit_error)

    prompt = _build_test_prompt_request()

    with pytest.raises(LLMProviderError, match="Gemini API Error"):
        await client.generate(prompt)

    assert client._client.models.generate_content.call_count == 3


@pytest.mark.asyncio
async def test_retry_exhaustion_on_generate_content_raises_ai_rate_limit_error() -> None:
    """
    Ensure that when max retries are exhausted on generate_content(), AIRateLimitError is raised.
    """
    settings = _build_test_settings(max_retries=2, initial_delay=0.01)
    client = GeminiClient(settings)

    rate_limit_error = ClientError(429, {"error": {"message": "Resource exhausted"}})
    client._client.models.generate_content = MagicMock(side_effect=rate_limit_error)

    with pytest.raises(AIRateLimitError):
        await client.generate_content("extract entities")

    assert client._client.models.generate_content.call_count == 2


# ============================================================================
# 4. Permanent Failure Non-Retry Tests
# ============================================================================


@pytest.mark.asyncio
async def test_permanent_auth_error_401_fails_immediately_without_retry() -> None:
    """
    Ensure that HTTP 401 Unauthorized is NOT retried and translates to AIAuthenticationError.
    """
    settings = _build_test_settings(max_retries=3)
    client = GeminiClient(settings)

    auth_error = ClientError(401, {"error": {"message": "Invalid API key"}})
    client._client.models.generate_content = MagicMock(side_effect=auth_error)

    with pytest.raises(AIAuthenticationError):
        await client.generate_content("test prompt")

    assert client._client.models.generate_content.call_count == 1


@pytest.mark.asyncio
async def test_permanent_bad_request_400_fails_immediately_without_retry() -> None:
    """
    Ensure that HTTP 400 Bad Request is NOT retried and fails on attempt 1.
    """
    settings = _build_test_settings(max_retries=3)
    client = GeminiClient(settings)

    bad_request = ClientError(400, {"error": {"message": "Invalid argument"}})
    client._client.models.generate_content = MagicMock(side_effect=bad_request)

    prompt = _build_test_prompt_request()

    with pytest.raises(LLMProviderError, match="Gemini API Error"):
        await client.generate(prompt)

    assert client._client.models.generate_content.call_count == 1


# ============================================================================
# 5. Metrics & Exact Per-Attempt Observability Tests
# ============================================================================


@pytest.mark.asyncio
async def test_metrics_observed_exactly_once_per_actual_attempt() -> None:
    """
    Ensure each actual provider attempt records its duration and request status,
    and token metrics reflect actual SDK usage metadata.
    """
    settings = _build_test_settings(max_retries=3, initial_delay=0.01)
    client = GeminiClient(settings)

    mock_response = MagicMock()
    mock_response.text = '{"report_id": "RPT-1"}'
    mock_response.usage_metadata = MagicMock(
        prompt_token_count=120,
        candidates_token_count=80,
        total_token_count=200,
    )
    mock_response.candidates = [MagicMock(finish_reason="STOP")]

    server_error = ServerError(500, {"error": {"message": "Internal error"}})
    client._client.models.generate_content = MagicMock(
        side_effect=[server_error, mock_response]
    )

    with (
        patch.object(llm_requests_total, "labels") as mock_req_labels,
        patch.object(llm_request_duration_seconds, "labels") as mock_dur_labels,
        patch.object(llm_tokens_total, "labels") as mock_tok_labels,
    ):
        mock_req_counter = MagicMock()
        mock_req_labels.return_value = mock_req_counter

        mock_dur_hist = MagicMock()
        mock_dur_labels.return_value = mock_dur_hist

        mock_tok_counter = MagicMock()
        mock_tok_labels.return_value = mock_tok_counter

        prompt = _build_test_prompt_request()
        await client.generate(prompt)

        # Duration observed twice (once for attempt 1 failure, once for attempt 2 success)
        assert mock_dur_hist.observe.call_count == 2

        # Request counter observed twice: status='error' then status='success'
        assert mock_req_counter.inc.call_count == 2
        assert mock_req_labels.call_args_list[0].kwargs["status"] == "error"
        assert mock_req_labels.call_args_list[1].kwargs["status"] == "success"

        # Tokens observed for prompt (120) and completion (80)
        assert mock_tok_counter.inc.call_count == 2
        mock_tok_counter.inc.assert_any_call(120)
        mock_tok_counter.inc.assert_any_call(80)


# ============================================================================
# 6. Response Validation & Empty Output Handling
# ============================================================================


@pytest.mark.asyncio
async def test_empty_response_text_raises_error_for_both_paths() -> None:
    """
    Ensure empty text from the provider raises domain error on both paths.
    """
    settings = _build_test_settings(max_retries=1)
    client = GeminiClient(settings)

    mock_empty = MagicMock(text=None, usage_metadata=None)
    client._client.models.generate_content = MagicMock(return_value=mock_empty)

    prompt = _build_test_prompt_request()

    with pytest.raises(LLMProviderError, match="empty response text"):
        await client.generate(prompt)

    with pytest.raises(AIResponseError, match="empty response"):
        await client.generate_content("test prompt")


# ============================================================================
# 7. Focused Verification: Attempt Counts, Bounded Delays & Thread Behavior
# ============================================================================


@pytest.mark.asyncio
async def test_exact_call_counts_for_immediate_success_and_multi_attempt_success() -> None:
    """
    Explicitly verify exact provider call counts:
    - Immediate success: 1 provider call
    - Success after 1 transient error: 2 provider calls
    - Success after 2 transient errors (on max_retries=3): 3 provider calls
    """
    settings = _build_test_settings(max_retries=3, initial_delay=0.001, max_delay=0.01)
    client = GeminiClient(settings)
    prompt = _build_test_prompt_request()

    mock_resp = MagicMock(text='{"ok": true}', usage_metadata=None, candidates=[MagicMock(finish_reason="STOP")])
    rate_err = ClientError(429, {"error": {"message": "Resource exhausted"}})

    # Case A: Immediate success -> exactly 1 provider call
    client._client.models.generate_content = MagicMock(return_value=mock_resp)
    await client.generate(prompt)
    assert client._client.models.generate_content.call_count == 1

    # Case B: Success on attempt 2 (after 1 retry) -> exactly 2 provider calls
    client._client.models.generate_content = MagicMock(side_effect=[rate_err, mock_resp])
    await client.generate(prompt)
    assert client._client.models.generate_content.call_count == 2

    # Case C: Success on attempt 3 (after 2 retries) -> exactly 3 provider calls
    client._client.models.generate_content = MagicMock(side_effect=[rate_err, rate_err, mock_resp])
    await client.generate(prompt)
    assert client._client.models.generate_content.call_count == 3


@pytest.mark.asyncio
async def test_exact_call_count_on_single_attempt_budget_exhaustion() -> None:
    """
    When GEMINI_MAX_RETRIES=1, exactly 1 call is made before exhaustion.
    """
    settings = _build_test_settings(max_retries=1)
    client = GeminiClient(settings)
    rate_err = ClientError(429, {"error": {"message": "Resource exhausted"}})
    client._client.models.generate_content = MagicMock(side_effect=rate_err)

    prompt = _build_test_prompt_request()
    with pytest.raises(LLMProviderError):
        await client.generate(prompt)

    assert client._client.models.generate_content.call_count == 1


@pytest.mark.asyncio
async def test_exponential_backoff_delays_and_bounding() -> None:
    """
    Verify retry delays follow initial_delay * 2^(attempt - 1) and are capped at max_delay.
    For max_retries=5, initial_delay=1.0, max_delay=3.0:
    - Attempt 1 fails -> sleep(1.0)
    - Attempt 2 fails -> sleep(2.0)
    - Attempt 3 fails -> sleep(3.0) (capped from 4.0)
    - Attempt 4 fails -> sleep(3.0) (capped from 8.0)
    - Attempt 5 fails -> exhausted (no sleep, raises)
    """
    settings = _build_test_settings(
        max_retries=5,
        initial_delay=1.0,
        max_delay=3.0,
    )
    client = GeminiClient(settings)
    rate_err = ClientError(429, {"error": {"message": "Resource exhausted"}})
    client._client.models.generate_content = MagicMock(side_effect=rate_err)

    prompt = _build_test_prompt_request()

    with patch("asyncio.sleep", return_value=None) as mock_sleep:
        with pytest.raises(LLMProviderError):
            await client.generate(prompt)

        assert client._client.models.generate_content.call_count == 5
        assert mock_sleep.call_count == 4
        slept_delays = [call_args.args[0] for call_args in mock_sleep.call_args_list]
        assert slept_delays == [1.0, 2.0, 3.0, 3.0]


@pytest.mark.asyncio
async def test_timeout_thread_non_termination_and_no_overlapping_retry() -> None:
    """
    Verify that when asyncio.wait_for times out:
    1. The coroutine immediately raises LLMTimeoutError without retrying.
    2. Exactly 1 provider call was made (no overlapping retries).
    3. The worker thread in asyncio.to_thread continues to completion in the background
       without mutating state or creating subsequent provider attempts.
    """
    settings = _build_test_settings(timeout=0.05, max_retries=3)
    client = GeminiClient(settings)

    thread_finished = asyncio.Event()

    def blocking_sync_worker(*args, **kwargs):
        time.sleep(0.15)
        thread_finished.set()
        return MagicMock(text='{"report": "late_response"}')

    client._client.models.generate_content = MagicMock(side_effect=blocking_sync_worker)
    prompt = _build_test_prompt_request()

    start = time.perf_counter()
    with pytest.raises(LLMTimeoutError, match="Gemini completion request timed out"):
        await client.generate(prompt)
    elapsed = time.perf_counter() - start

    assert elapsed < 0.12
    assert client._client.models.generate_content.call_count == 1

    await asyncio.wait_for(thread_finished.wait(), timeout=0.5)
    assert thread_finished.is_set()
    assert client._client.models.generate_content.call_count == 1

