# 📡 SentinelGraph AI: REST API Reference

## 1. Overview & API Conventions

SentinelGraph AI exposes an asynchronous HTTP REST API powered by FastAPI. The API contract is defined using Pydantic V2 data models and OpenAPI 3.1 specifications.

### Base URLs & OpenAPI Documentation
* **Local Direct API**: `http://localhost:8000`
* **Full-Stack Ingress (Nginx)**: `http://localhost/api` (or relative path in web console)
* **Interactive Swagger UI**: `http://localhost:8000/docs`
* **ReDoc Reference**: `http://localhost:8000/redoc`
* **OpenAPI 3.1 JSON Specification**: `http://localhost:8000/api/v1/openapi.json`

![FastAPI Swagger UI](../visuals/swagger.png)
*FastAPI Interactive Swagger UI (`/docs`) exposing all complaint, graph, timeline, and investigation API endpoints with interactive schema exploration.*

### Distributed Tracing Header (`X-Request-ID`)
Every request accepted by the API is tagged with an `X-Request-ID` correlation identifier:
* If provided by the client in the request header (`X-Request-ID: <custom-uuid>`), that ID is preserved.
* If omitted, the [`RequestLoggingMiddleware`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/core/middleware.py) generates a fresh UUID4 string.
* The correlation ID is injected into every response header:
  ```http
  X-Request-ID: 7b89f022-44ef-4b45-9831-50e5eb54199c
  ```
* All application logs for the request are contextualized with this ID for end-to-end debugging.

### Standard Error Response Format
All error responses adhere to standard JSON error structures:
```json
{
  "detail": "Descriptive error message or validation error details"
}
```

---

## 2. Authentication & Authorization Reality

> [!WARNING]
> **Authentication is currently NOT implemented.**
> The API operates in an open, unauthenticated state intended for evaluation, hackathon judging, and local research.

### Auth Placeholder Route
* **Endpoint**: `GET /api/v1/auth/`
* **Summary**: Authentication placeholder endpoint
* **Response (HTTP 200 OK)**:
  ```json
  {
    "message": "Coming soon"
  }
  ```
Do **NOT** attempt to supply JWT tokens, Bearer tokens, or API keys to `/api/v1/auth/`. Production deployment hardening will integrate OAuth2/OIDC and role-based access control (RBAC).

---

## 3. Operational Health & Telemetry Endpoints

### 3.1 Liveness Probe
* **Route**: `GET /health/live` (Also accessible at `/api/v1/health/live`)
* **Tags**: `Health`, `General`
* **Summary**: Kubernetes / container process liveness check.
* **Behavior**: Always returns HTTP 200 OK while the Python asyncio event loop is responsive. Does not touch databases.
* **Response Model**: `LivenessResponse`
  ```json
  {
    "status": "healthy"
  }
  ```

---

### 3.2 Readiness Probe
* **Route**: `GET /health/ready` (Also accessible at `/api/v1/health/ready`)
* **Tags**: `Health`, `General`
* **Summary**: Traffic routing readiness check.
* **Behavior**: Probes critical dependencies (PostgreSQL and Neo4j) and returns HTTP 200 when operational, or HTTP 503 when degraded/unready.
* **Response Model**: `ReadinessResponse`
  ```json
  {
    "status": "healthy",
    "is_ready": true,
    "dependencies": {
      "postgres": {
        "status": "healthy",
        "latency_ms": 2.45
      },
      "neo4j": {
        "status": "healthy",
        "latency_ms": 4.12
      },
      "gemini": {
        "status": "healthy",
        "latency_ms": 112.50
      }
    }
  }
  ```

---

### 3.3 Health Diagnostic Summary
* **Route**: `GET /health` (Also accessible at `/api/v1/health`)
* **Tags**: `Health`, `General`
* **Summary**: Detailed operational health report.
* **Response Model**: `HealthSummaryResponse`
  ```json
  {
    "status": "healthy",
    "service": "SentinelGraph AI",
    "version": "1.0.0",
    "environment": "production",
    "dependencies": {
      "postgres": { "status": "healthy", "latency_ms": 2.10 },
      "neo4j": { "status": "healthy", "latency_ms": 3.85 },
      "gemini": { "status": "healthy", "latency_ms": 98.40 }
    }
  }
  ```

---

### 3.4 Prometheus Metrics
* **Route**: `GET /metrics`
* **Tags**: `Metrics`
* **Summary**: Exposes standard Prometheus text metrics.
* **Status**: HTTP 200 OK
* **Content-Type**: `text/plain; version=0.0.4; charset=utf-8`

---

### 3.5 System Version
* **Route**: `GET /api/v1/version/`
* **Tags**: `General`
* **Response**:
  ```json
  {
    "version": "1.0.0"
  }
  ```

---

## 4. Complaints Management API

Mounted under `/api/v1/complaints`.

### 4.1 Report a New Complaint
* **Route**: `POST /api/v1/complaints/`
* **Summary**: Submit a fraud complaint into PostgreSQL and trigger background graph ingestion.
* **Status**: HTTP 201 Created
* **Request Body (`IncidentCreate`)**:
  ```json
  {
    "title": "Digital Arrest Coercion Scam",
    "description": "Victim received WhatsApp call from +919876543210 claiming to be CBI Officer Rajesh Sharma. Victim was instructed to transfer Rs 50,000 to fraudster@okhdfcbank to clear customs.",
    "reporter_type": "citizen",
    "source": "web_portal",
    "priority": "high",
    "scam_category": "digital_arrest",
    "case_reference": "FIR-2026-DEL-8891"
  }
  ```
* **Response Body (`IncidentResponse`)**:
  ```json
  {
    "id": "3d3cf359-8812-4021-9988-123456789abc",
    "title": "Digital Arrest Coercion Scam",
    "description": "Victim received WhatsApp call from...",
    "reporter_type": "citizen",
    "source": "web_portal",
    "status": "new",
    "priority": "high",
    "scam_category": "digital_arrest",
    "case_reference": "FIR-2026-DEL-8891",
    "ai_summary": null,
    "risk_score": null,
    "graph_node_id": null,
    "created_at": "2026-09-12T08:00:00Z",
    "updated_at": "2026-09-12T08:00:00Z"
  }
  ```

---

### 4.2 List Complaints (Paginated)
* **Route**: `GET /api/v1/complaints/`
* **Summary**: Retrieve a paginated list of recorded complaints.
* **Query Parameters**:
  * `skip` (integer, default: `0`, ge: `0`): Records to bypass.
  * `limit` (integer, default: `100`, ge: `1`, le: `500`): Maximum records to return.
* **Response Body (`list[IncidentListResponse]`)**:
  ```json
  [
    {
      "id": "3d3cf359-8812-4021-9988-123456789abc",
      "title": "Digital Arrest Coercion Scam",
      "reporter_type": "citizen",
      "status": "analyzed",
      "priority": "high",
      "scam_category": "digital_arrest",
      "case_reference": "FIR-2026-DEL-8891",
      "graph_node_id": "complaint:3d3cf359-8812-4021-9988-123456789abc",
      "risk_score": 0.85,
      "created_at": "2026-09-12T08:00:00Z"
    }
  ]
  ```

---

### 4.3 Get Single Complaint
* **Route**: `GET /api/v1/complaints/{incident_id}`
* **Summary**: Retrieve full complaint details by UUID.
* **Path Parameter**: `incident_id` (UUID string).
* **Response**: `IncidentResponse` (HTTP 200 OK) or `HTTP 404 Not Found` if missing.

---

## 5. Graph Intelligence API

Mounted under `/api/v1/graph`.

| Method | Path | Summary | Query / Path Params | Response Model |
| :--- | :--- | :--- | :--- | :--- |
| **GET** | `/api/v1/graph/entity/{value}` | Retrieve single graph node | `value` (str) | `GraphNode` |
| **GET** | `/api/v1/graph/entity/{value}/neighbors` | 1-hop connected neighbors | `value` (str) | `GraphNeighborsResponse` |
| **GET** | `/api/v1/graph/entity/{value}/incidents` | Connected complaints | `value` (str) | `RelatedIncidentsResponse` |
| **GET** | `/api/v1/graph/entity/{value}/risk` | Entity risk assessment | `value` (str) | `EntityRiskResponse` |
| **GET** | `/api/v1/graph/entity/{value}/ring` | Multi-hop fraud ring component | `value` (str) | `FraudRingResponse` |
| **GET** | `/api/v1/graph/network/summary` | Global graph statistics | None | `NetworkSummaryResponse` |
| **GET** | `/api/v1/graph/network/top-risk` | Highest risk entities | `limit` (default: 10, 1-100) | `list[TopRiskEntityResponse]` |
| **GET** | `/api/v1/graph/path` | Shortest path between 2 nodes | `source` (str), `target` (str) | `PathResponse` |
| **GET** | `/api/v1/graph/entity/{value}/shared` | Complaints sharing this entity | `value` (str) | `SharedEntityResponse` |

---

## 6. Graph Visualization API

Mounted under `/api/v1/graph`.

### Subgraph Visualization for Cytoscape.js
* **Route**: `GET /api/v1/graph/visualization/{node_id}`
* **Tags**: `Graph Visualization`
* **Summary**: Retrieve a subgraph centered around a target node formatted for Cytoscape.js.
* **Path Parameter**: `node_id` (str, e.g. `phone:+919876543210` or `complaint:<uuid>`).
* **Query Parameter**: `depth` (integer, default: `2`, min: `1`, max: `5`).
* **Response Model (`GraphResponse`)**:
  ```json
  {
    "nodes": [
      {
        "id": "phone:+919876543210",
        "label": "Phone",
        "properties": {
          "value": "+919876543210",
          "confidence": 0.95
        }
      },
      {
        "id": "complaint:3d3cf359-8812-4021-9988-123456789abc",
        "label": "Complaint",
        "properties": {
          "complaint_id": "3d3cf359-8812-4021-9988-123456789abc"
        }
      }
    ],
    "edges": [
      {
        "source": "complaint:3d3cf359-8812-4021-9988-123456789abc",
        "target": "phone:+919876543210",
        "type": "MENTIONS",
        "properties": {}
      }
    ],
    "metadata": {
      "node_count": 2,
      "edge_count": 1,
      "root_node": "phone:+919876543210",
      "depth": 2
    }
  }
  ```

---

## 7. Analytics API

Mounted under `/api/v1/analytics`.

* **`GET /api/v1/analytics/summary`**: Overall node counts, relationship counts, and distribution by entity label. Returns `GraphSummary`.
* **`GET /api/v1/analytics/top-connected`**: Entities with highest degree centrality (most connected complaints). Returns `list[TopConnectedEntity]`.
* **`GET /api/v1/analytics/shared-entities`**: Discovers entities shared across $\ge 2$ complaints (`minimum_complaints` parameter). Returns `list[SharedEntityAnalysis]`.

---

## 8. Timeline Engine API

Mounted under `/api/v1/timeline`.

### Reconstruct Chronological Timeline
* **Route**: `GET /api/v1/timeline/{entity_value}`
* **Summary**: Reconstructs the multi-hop timeline of connected complaints and entity occurrences for an investigated entity.
* **Path Parameter**: `entity_value` (e.g. `+919876543210` or `scammer@upi`).
* **Response Model (`TimelineResponse`)**:
  ```json
  {
    "entity": {
      "value": "+919876543210",
      "type": "Phone",
      "first_seen": "2026-08-01T10:00:00Z",
      "last_seen": "2026-08-20T14:30:00Z",
      "total_complaints": 4
    },
    "events": [
      {
        "event_id": "EVT-001",
        "timestamp": "2026-08-01T10:00:00Z",
        "event_type": "FIRST_APPEARANCE",
        "complaint_id": "C-101",
        "description": "Initial complaint registered involving phone +919876543210"
      }
    ],
    "statistics": {
      "total_complaints": 4,
      "total_entities": 7,
      "phone_count": 2,
      "upi_count": 2
    },
    "insights": [
      {
        "insight_type": "BURST_ACTIVITY",
        "severity": "HIGH",
        "message": "3 complaints recorded within a 48-hour window."
      }
    ]
  }
  ```

---

## 9. Investigation & AI Report API

Mounted under `/api/v1/investigation`.

### 9.1 Graph-RAG Investigation
* **Route**: `POST /api/v1/investigation/`
* **Summary**: Perform Graph-RAG evidence gathering and generate initial investigation report.
* **Request Body (`InvestigationRequest`)**:
  ```json
  {
    "target_type": "phone",
    "target_value": "+919876543210"
  }
  ```
* **Response Body (`InvestigationResponse`)**: Contains `evidence` (neighbors, related incidents, risk, fraud ring) and `report` (summary, risk level, confidence, findings).

---

### 9.2 Professional Investigation Report
* **Route**: `POST /api/v1/investigation/report`
* **Summary**: Execute complete deterministic analysis, compile canonical case file, format via Gemini with SHA-256 fingerprinting, and validate against Pydantic schema.
* **Status**: HTTP 200 OK
* **Request Body (`InvestigationRequest`)**:
  ```json
  {
    "target_type": "upi",
    "target_value": "scammer@upi"
  }
  ```
* **Response Body (`ProfessionalInvestigationReport`)**:
  ```json
  {
    "report_id": "REP-20260912-7B89F022",
    "correlation_id": "CORR-A1B2C3D4E5",
    "prompt_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "executive_summary": "Comprehensive fraud dossier investigating UPI VPA scammer@upi...",
    "risk_level": "CRITICAL",
    "overall_risk_score": 92.5,
    "confidence_score": 0.96,
    "risk_justification": "Target identifier is linked to 5 verified citizen complaints with active infrastructure expansion.",
    "key_takeaways": [
      "Target UPI ID reused across 5 distinct digital arrest complaints",
      "Network evolved from single-complaint phone usage to multi-tier UPI collect links"
    ],
    "findings": [
      {
        "finding_id": "FIND-001",
        "title": "High Volume Financial Identifier Reuse",
        "description": "UPI VPA scammer@upi is directly linked to 5 independent citizen complaints.",
        "severity": "CRITICAL",
        "confidence": 0.95,
        "citations": [
          { "citation_id": "C-101", "type": "complaint" },
          { "citation_id": "scammer@upi", "type": "entity" }
        ]
      }
    ],
    "recommendations": [
      {
        "recommendation_id": "REC-001",
        "action": "Immediate Financial Freeze on UPI VPA scammer@upi",
        "priority": "CRITICAL",
        "reason": "Exceeds 3-complaint syndicate threshold under Digital Public Safety guidelines.",
        "target_entities": ["scammer@upi"]
      }
    ],
    "telemetry": {
      "model_name": "gemini-2.5-flash",
      "latency_ms": 1420.5,
      "prompt_tokens": 1250,
      "completion_tokens": 680,
      "total_tokens": 1930
    }
  }
  ```

#### Error Codes for Report Generation
* `HTTP 404 Not Found`: Target entity does not exist in the Neo4j knowledge graph.
* `HTTP 422 Unprocessable Entity`: Prompt validation failure or LLM output schema non-compliance.
* `HTTP 502 Bad Gateway`: Non-retryable Gemini provider failure or retry budget exhaustion.
* `HTTP 504 Gateway Timeout`: Gemini inference call exceeded `GEMINI_TIMEOUT_SECONDS`.
