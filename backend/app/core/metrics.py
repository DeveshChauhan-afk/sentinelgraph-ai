# app/core/metrics.py

"""
Core metrics registry and metric definitions using the default Prometheus registry.

Provides framework-independent metric collectors for tracking HTTP request
volume, status codes, and latency distributions.
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
