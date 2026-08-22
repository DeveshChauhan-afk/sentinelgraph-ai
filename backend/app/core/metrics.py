# app/core/metrics.py

"""
Core metrics registry and metric definitions using the default Prometheus registry.

Provides framework-independent metric collectors for tracking HTTP request
volume, status codes, latency distributions, and LLM inference telemetry.
"""

from prometheus_client import Counter, Histogram

# Standard latency buckets (in seconds) suited for HTTP service monitoring:
# 5ms, 10ms, 25ms, 50ms, 75ms, 100ms, 250ms, 500ms, 750ms, 1.0s, 2.5s, 5.0s, 7.5s, 10.0s
HTTP_REQUEST_DURATION_BUCKETS: tuple[float, ...] = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.075,
    0.1,
    0.25,
    0.5,
    0.75,
    1.0,
    2.5,
    5.0,
    7.5,
    10.0,
)

# Standard latency buckets (in seconds) suited for LLM inference monitoring:
# 100ms, 250ms, 500ms, 1.0s, 2.5s, 5.0s, 10.0s, 20.0s, 30.0s, 60.0s
LLM_REQUEST_DURATION_BUCKETS: tuple[float, ...] = (
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    20.0,
    30.0,
    60.0,
)

# ============================================================================
# HTTP Infrastructure Metrics
# ============================================================================

# 1. Total HTTP Requests Counter
http_requests_total: Counter = Counter(
    name="http_requests_total",
    documentation="Total number of HTTP requests processed.",
    labelnames=["method", "path", "status_code"],
)

# 2. HTTP Request Duration Histogram
http_request_duration_seconds: Histogram = Histogram(
    name="http_request_duration_seconds",
    documentation="HTTP request processing duration in seconds.",
    labelnames=["method", "path"],
    buckets=HTTP_REQUEST_DURATION_BUCKETS,
)

# ============================================================================
# LLM / AI Telemetry Metrics
# ============================================================================

# 3. Total LLM Requests Counter
llm_requests_total: Counter = Counter(
    name="llm_requests_total",
    documentation="Total number of LLM completion requests processed.",
    labelnames=["provider", "model", "status"],
)

# 4. LLM Request Duration Histogram
llm_request_duration_seconds: Histogram = Histogram(
    name="llm_request_duration_seconds",
    documentation="LLM completion request processing duration in seconds.",
    labelnames=["provider", "model"],
    buckets=LLM_REQUEST_DURATION_BUCKETS,
)

# 5. Total LLM Tokens Counter
llm_tokens_total: Counter = Counter(
    name="llm_tokens_total",
    documentation="Total number of LLM tokens processed.",
    labelnames=["provider", "model", "type"],
)
