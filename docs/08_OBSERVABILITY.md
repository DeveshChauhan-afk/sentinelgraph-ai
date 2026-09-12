# 📊 SentinelGraph AI: Observability, Metrics & Health Diagnostics

## 1. Observability Architecture Overview

SentinelGraph AI incorporates an enterprise observability stack built around open standards:
1. **Prometheus Client Library**: Embedded inside the FastAPI backend, tracking HTTP transactions and LLM inference telemetry.
2. **Prometheus Time-Series Engine (v2.53)**: Periodically scrapes metrics every 15 seconds and evaluates alert expressions.
3. **Alertmanager Specification**: Five production alert rules defined in `monitoring/prometheus/alerts.yml`.
4. **Grafana Operations Dashboard (v11.1)**: Pre-provisioned operational dashboard providing single-pane visibility into system health.
5. **Modular Health Checking Subsystem**: Standardized Kubernetes-ready probes (`/health/live`, `/health/ready`, `/health`).
6. **Distributed Tracing & Contextual Logging**: Ingress correlation via `X-Request-ID` and Loguru structured JSON logging.

```
┌────────────────────────────────────────────────────────┐
│                   FastAPI Application                  │
│  • RequestLoggingMiddleware (X-Request-ID Injection)   │
│  • Prometheus Client (Counters, Histograms)            │
│  • Modular Health Checkers (Postgres, Neo4j, Gemini)   │
└──────────────┬──────────────────────────┬──────────────┘
               │                          │
      Scrape   │ HTTP /metrics            │ HTTP /health/ready
      (15s)    ▼                          ▼
┌─────────────────────────────┐   ┌──────────────────────┐
│  Prometheus Engine (v2.53)  │   │ Container Orchestrator│
│  • prometheus.yml           │   │ (Docker / Kubernetes) │
│  • alerts.yml (5 Rules)     │   │ Readiness Routing     │
└──────────────┬──────────────┘   └──────────────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Grafana Dashboard (v11.1)  │
│  • sentinelgraph-operations │
│  • Throughput, Latency, AI  │
└─────────────────────────────┘
```

---

## 2. Prometheus Metrics Catalog

All metrics are exposed at `GET /metrics` in standard Prometheus text exposition format:

### 2.1 HTTP Infrastructure Metrics
Defined in [`app/core/metrics.py`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/core/metrics.py):

| Metric Name | Type | Labels | Description |
| :--- | :--- | :--- | :--- |
| `http_requests_total` | Counter | `method`, `path`, `status_code` | Total count of all HTTP requests processed by the application. |
| `http_request_duration_seconds` | Histogram | `method`, `path` | Request execution latency in seconds with calibrated percentile buckets. |

#### Latency Histogram Buckets
The histogram utilizes exponential buckets optimized for web APIs:
`[0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0]`.

---

### 2.2 LLM / Gemini Inference Metrics
Tracks generative AI performance, availability, and API token economics:

| Metric Name | Type | Labels | Description |
| :--- | :--- | :--- | :--- |
| `llm_requests_total` | Counter | `provider`, `model`, `status` | Total AI model invocations (`status="success"` or `status="error"`). |
| `llm_request_duration_seconds`| Histogram | `provider`, `model` | Per-call inference latency in seconds. |
| `llm_tokens_total` | Counter | `provider`, `model`, `type` | Total tokens consumed (`type="prompt"` or `type="completion"`). |

#### Token Telemetry Extraction
Token metrics are extracted directly from Google Gemini's `usage_metadata` upon successful completion:
```python
usage_meta = getattr(response, "usage_metadata", None)
if usage_meta:
    prompt_tokens = getattr(usage_meta, "prompt_token_count", 0)
    completion_tokens = getattr(usage_meta, "candidates_token_count", 0)
    llm_tokens_total.labels(provider="gemini", model=model_name, type="prompt").inc(prompt_tokens)
    llm_tokens_total.labels(provider="gemini", model=model_name, type="completion").inc(completion_tokens)
```

---

## 3. Prometheus Scrape Configuration

Prometheus is configured in [`monitoring/prometheus/prometheus.yml`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/monitoring/prometheus/prometheus.yml):

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  scrape_timeout: 10s

rule_files:
  - "/etc/prometheus/alerts.yml"

scrape_configs:
  # 1. SentinelGraph AI FastAPI Backend
  - job_name: "sentinelgraph-backend"
    metrics_path: "/metrics"
    scrape_interval: 15s
    scrape_timeout: 10s
    static_configs:
      - targets: ["api:8000"]
        labels:
          service: "sentinelgraph-backend"
          environment: "production"

  # 2. Prometheus Self-Monitoring
  - job_name: "prometheus"
    metrics_path: "/metrics"
    scrape_interval: 15s
    static_configs:
      - targets: ["localhost:9090"]
        labels:
          service: "prometheus"
```

---

## 4. Production Alert Rules (The 5 Core Rules)

Defined in [`monitoring/prometheus/alerts.yml`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/monitoring/prometheus/alerts.yml):

```yaml
groups:
  - name: sentinelgraph_alerts
    rules:
      # Rule 1: Critical Server Error Rate
      - alert: HighHttp5xxErrorRate
        expr: >-
          (sum(rate(http_requests_total{status_code=~"5.."}[5m])) or vector(0))
          /
          (sum(rate(http_requests_total[5m])) > 0)
          > 0.05
        for: 5m
        labels:
          severity: critical
          service: sentinelgraph-backend
        annotations:
          summary: "High HTTP 5xx error rate detected on SentinelGraph AI backend"
          description: "HTTP 5xx error rate is above 5% over the last 5 minutes."

      # Rule 2: Degrading API Latency
      - alert: ElevatedHttpRequestLatency
        expr: >-
          histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, path))
          > 2.0
        for: 5m
        labels:
          severity: warning
          service: sentinelgraph-backend
        annotations:
          summary: "Elevated HTTP request latency detected"
          description: "95th percentile HTTP latency for path '{{ $labels.path }}' is above 2.0s over 5m."

      # Rule 3: Database / Infrastructure Outage
      - alert: ReadinessProbeFailing
        expr: >-
          sum(rate(http_requests_total{path=~".*/health/ready", status_code="503"}[5m]))
          > 0
        for: 2m
        labels:
          severity: critical
          service: sentinelgraph-backend
        annotations:
          summary: "SentinelGraph AI readiness probe is failing"
          description: "Readiness probe returning HTTP 503, indicating unhealthy dependencies."

      # Rule 4: Generative AI Provider Failure Rate
      - alert: HighLlmErrorRate
        expr: >-
          (sum(rate(llm_requests_total{status="error"}[5m])) or vector(0))
          /
          (sum(rate(llm_requests_total[5m])) > 0)
          > 0.10
        for: 5m
        labels:
          severity: critical
          service: sentinelgraph-backend
        annotations:
          summary: "High LLM error rate detected during AI inference"
          description: "LLM completion error rate is above 10% over the last 5 minutes."

      # Rule 5: Generative AI Latency Spike
      - alert: ElevatedLlmRequestLatency
        expr: >-
          histogram_quantile(0.95, sum(rate(llm_request_duration_seconds_bucket[5m])) by (le, model))
          > 15.0
        for: 5m
        labels:
          severity: warning
          service: sentinelgraph-backend
        annotations:
          summary: "Elevated LLM inference latency detected"
          description: "95th percentile LLM latency for model '{{ $labels.model }}' is above 15.0s over 5m."
```

---

## 5. Grafana Operations Dashboard

Grafana is provisioned automatically with pre-configured datasources and dashboards:
* **Dashboard File**: [`monitoring/grafana/dashboards/sentinelgraph-operations.json`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/monitoring/grafana/dashboards/sentinelgraph-operations.json)
* **Access**: `http://localhost:3000` (Default credentials: `admin` / `admin`).
* **Visual Panels**:
  1. **HTTP Request Rate**: Total operations per second split by HTTP status code (`2xx`, `4xx`, `5xx`).
  2. **API Latency Quantiles**: p50, p95, and p99 response times per endpoint.
  3. **Dependency Health Status**: Live status of PostgreSQL, Neo4j, and Google Gemini.
  4. **LLM Inference Throughput**: Successful vs errored Gemini completions per minute.
  5. **LLM Inference Latency**: p95 execution duration for entity extraction and report formatting.
  6. **Token Consumption Rate**: Prompt tokens vs completion tokens consumed per minute.

---

## 6. Modular Health Probes Subsystem

The application implements a dedicated health architecture under [`app/core/health/`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/core/health/):

```
                       HealthService
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
PostgresHealthChecker Neo4jHealthChecker  GeminiHealthChecker
  (SELECT 1 ping)      (RETURN 1 cypher)   (Client Validation)
```

### 6.1 Liveness Probe (`GET /health/live`)
* **Purpose**: Verifies that the container process is running and the Python asyncio event loop is responsive.
* **Return**: HTTP 200 OK (`{"status": "healthy"}`).

### 6.2 Readiness Probe (`GET /health/ready`)
* **Purpose**: Verifies that the container is ready to accept user traffic.
* **Checks**: Executes lightweight pings against PostgreSQL (`SELECT 1`) and Neo4j (`RETURN 1;`).
* **Return**:
  * HTTP 200 OK when critical dependencies are operational.
  * HTTP 503 Service Unavailable when either database connection is broken.

### 6.3 Diagnostic Summary (`GET /health`)
* **Purpose**: Human-readable and automated diagnostic check.
* **Return**: Always returns HTTP 200 with structured JSON reporting latency and health status for each subsystem.
