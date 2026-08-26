# SentinelGraph AI: API Reference & Integration Guide

## 1. Overview

SentinelGraph AI provides an asynchronous REST API built with FastAPI for fraud intelligence, Graph-RAG investigations, and public safety data management.

* **API Prefix**: All functional application endpoints are served under the `/api/v1` route prefix.
* **Interactive Documentation**: Interactive API testing and exploration interfaces are available at:
  * Swagger UI: [`/docs`](file:///docs)
  * ReDoc: [`/redoc`](file:///redoc)
* **OpenAPI Schema**: The raw OpenAPI 3.1 JSON schema is exposed at `/api/v1/openapi.json`.
* **Scope**: This document serves as a human-readable reference and integration guide for backend developers and operators, focusing on route capabilities, parameters, and error behavior without duplicating generated OpenAPI schemas.

### Request Correlation (`X-Request-ID`)
SentinelGraph AI implements distributed request correlation across all HTTP endpoints via `RequestLoggingMiddleware`:
* **Client-Provided IDs**: Clients may supply a custom correlation identifier in the inbound `X-Request-ID` header.
* **Automatic Generation**: If omitted, the middleware generates a new standard UUID4 string.
* **Response Header**: The active `X-Request-ID` is echoed in every HTTP response header.
* **Log Correlation**: The request ID is bound to the async execution context (`ContextVar`) and included in all structured Loguru log entries emitted during request handling.

---

## 2. Operational & Health Endpoints

Operational probes, Prometheus metrics, and live documentation endpoints are exposed directly at the root level:

### `GET /health`
* **Purpose**: Comprehensive diagnostic health summary of the application and its critical dependencies.
* **Dependencies Checked**: PostgreSQL database, Neo4j AuraDB graph connection, and Google Gemini API readiness.
* **Response Model**: `HealthSummaryResponse` (JSON containing overall `status`, service metadata, environment, and individual dependency states: `healthy`, `degraded`, or `unhealthy`).
* **Status Code**: `200 OK` (returns structured diagnostics even when components are degraded or unhealthy).

### `GET /health/live`
* **Purpose**: Lightweight process liveness probe for container orchestrators (e.g., Kubernetes, Docker).
* **Behavior**: Confirms the FastAPI event loop is responsive without executing external database queries.
* **Response Model**: `LivenessResponse` (`{"status": "alive"}`).
* **Status Code**: `200 OK`.

### `GET /health/ready`
* **Purpose**: Readiness probe for load balancers and ingress traffic routers.
* **Behavior**: Evaluates critical dependencies to determine if the instance can safely accept incoming traffic.
* **Response Model**: `ReadinessResponse` (`status`, `is_ready: bool`, and dependency details).
* **Status Codes**:
  * `200 OK`: Instance is ready to accept traffic (including `DEGRADED` operational states where non-blocking features remain functional).
  * `503 Service Unavailable`: Instance is unready (`UNHEALTHY` critical dependency failure).

> **Note**: In addition to the root routes above, the health endpoints are also mounted under the API version prefix via the main router:
> * `GET /api/v1/health`
> * `GET /api/v1/health/live`
> * `GET /api/v1/health/ready`

### `GET /metrics`
* **Purpose**: Prometheus metrics scrape endpoint.
* **Content Type**: `text/plain; version=0.0.4; charset=utf-8` (`CONTENT_TYPE_LATEST`).
* **Metrics Emitted**: Includes HTTP request counters (`http_requests_total`), request duration histograms (`http_request_duration_seconds`), and LLM telemetry (`llm_requests_total`, `llm_request_duration_seconds`, `llm_tokens_total`).
* **Status Code**: `200 OK`.

### `GET /docs`
* **Purpose**: Interactive Swagger UI client for executing live API requests against the running instance.
* **Content Type**: `text/html`.
* **Status Code**: `200 OK`.

### `GET /redoc`
* **Purpose**: Clean, three-panel ReDoc technical API documentation interface.
* **Content Type**: `text/html`.
* **Status Code**: `200 OK`.

### `GET /api/v1/openapi.json`
* **Purpose**: Machine-readable OpenAPI 3.1 schema definition for automated SDK generation and API contract validation.
* **Content Type**: `application/json`.
* **Status Code**: `200 OK`.

---

## 3. Complaint Intake & Management

The complaints API provides public endpoints for submitting fraud incidents and querying historical reports stored durably in the PostgreSQL database.

### `POST /api/v1/complaints/`
* **Purpose**: Submit a new fraud complaint for ingestion, persistence, and automated downstream AI entity extraction.
* **Request Body**: `IncidentCreate` (JSON payload containing `title`, `description`, `reporter_type`, `source`, `priority`, and optional `scam_category`, `case_reference`).
* **Response Model**: `IncidentResponse` (Full relational record including assigned `id` UUID, initial `status`, and timestamps).
* **Status Code**: `201 Created`.

### `GET /api/v1/complaints/`
* **Purpose**: Retrieve a paginated list of recorded fraud complaints.
* **Query Parameters**:
  * `skip` (*integer*, default: `0`): Number of records to skip for pagination.
  * `limit` (*integer*, default: `100`): Maximum number of records to return.
* **Response Model**: `list[IncidentListResponse]` (Array of summary complaint records with attached `graph_node_id` references).
* **Status Code**: `200 OK`.

### `GET /api/v1/complaints/{incident_id}`
* **Purpose**: Retrieve complete details of a specific fraud complaint by its unique identifier.
* **Path Parameters**:
  * `incident_id` (*UUID*): Primary key UUID of the incident record.
* **Response Model**: `IncidentResponse`.
* **Status Codes**:
  * `200 OK`: Complaint found and returned.
  * `404 Not Found`: No complaint exists with the specified UUID.

---

## 4. Graph-RAG & Explainable AI Investigation

The investigation API provides endpoints for executing Graph Retrieval-Augmented Generation (Graph-RAG) and generating deterministic Explainable AI (XAI) investigation reports.

> **Architectural Principle**: Deterministic backend services (*Timeline, Entity Analysis, Fraud Evolution, Evidence Engine*) perform 100% of the investigation analysis, risk assessment, and evidence correlation. The Large Language Model (Google Gemini) operates strictly as a structured report writer and synthesizer to format verified findings into professional legal-grade dossiers.

### `POST /api/v1/investigation/`
* **Purpose**: Execute Graph-RAG evidence aggregation and context retrieval across the Neo4j knowledge graph.
* **Request Body**: `InvestigationRequest` (JSON payload containing target entity details: `target_type` and `target_value`).
* **Response Model**: `InvestigationResponse` (Aggregated graph metrics, connected complaint evidence, network risk score, and Graph-RAG synthesis).
* **Status Codes**:
  * `200 OK`: Investigation successfully executed.
  * `404 Not Found`: Target entity not found in the graph knowledge base (`GraphEntityNotFoundError`).

### `POST /api/v1/investigation/report`
* **Purpose**: Generate an end-to-end validated, structured Explainable AI investigation report with explicit evidentiary grounding and citation tracking.
* **Pipeline Execution**:
  1. `InvestigationSummaryService` builds canonical deterministic case file.
  2. `ReportContextBuilder` compiles token-optimized context view with citation maps.
  3. `PromptBuilder` constructs prompt with SHA-256 fingerprinting (`prompt_hash`).
  4. `LLMClient` (Gemini) generates structured report document.
  5. `ReportParser` validates output schema and attaches execution telemetry.
* **Request Body**: `InvestigationRequest` (`target_type`, `target_value`).
* **Response Model**: `ProfessionalInvestigationReport` (Formal dossier with executive summary, confirmed entities, fraud evolution timeline, evidence citations `[Complaint: ...]`, and execution telemetry).
* **Status Codes**:
  * `200 OK`: Formal investigation report generated and schema-validated.
  * `404 Not Found`: Target entity not found in the graph (`GraphEntityNotFoundError`).
  * `422 Unprocessable Entity`: Prompt construction failure, invalid output schema, or JSON parsing error (`PromptValidationError`, `InvalidReportSchemaError`, `ReportParsingError`).
  * `502 Bad Gateway`: Upstream LLM provider service error (`LLMProviderError`).
  * `504 Gateway Timeout`: Upstream LLM provider request timed out (`LLMTimeoutError`).

---

## 5. Knowledge Graph & Topological Intelligence

The graph intelligence API provides endpoints for executing Cypher graph queries against Neo4j AuraDB.

> **Graph Topology**: The graph strictly models complaints and extracted entities connected via the single persisted relationship type:
> ```text
> (:Complaint)-[:MENTIONS]->(:Entity)
> ```
> Multi-hop fraud network connections and shared identifier clusters are evaluated through dynamic graph traversals across `MENTIONS` edges.

### `GET /api/v1/graph/entity/{value}`
* **Purpose**: Retrieve the graph node properties and metadata for a specific entity value.
* **Path Parameters**:
  * `value` (*string*): Normalized entity lookup value (e.g. phone number, UPI ID, bank account).
* **Response Model**: `GraphNode` (Node attributes including `id`, `value`, `confidence`, `lookup_value`).
* **Status Codes**:
  * `200 OK`: Entity found and returned.
  * `404 Not Found`: Entity not found in the graph knowledge base (`GraphEntityNotFoundError`).

### `GET /api/v1/graph/entity/{value}/neighbors`
* **Purpose**: Perform a 1-hop bidirectional neighbor expansion around an entity.
* **Path Parameters**:
  * `value` (*string*): Entity value to expand.
* **Response Model**: `GraphNeighborsResponse` (Center entity and list of directly connected neighbor nodes).
* **Status Codes**:
  * `200 OK`: Neighbor expansion completed.
  * `404 Not Found`: Center entity not found (`GraphEntityNotFoundError`).

### `GET /api/v1/graph/entity/{value}/incidents`
* **Purpose**: Retrieve all complaint nodes connected directly or through 2-hop traversals to the specified entity.
* **Path Parameters**:
  * `value` (*string*): Target entity value.
* **Response Model**: `RelatedIncidentsResponse` (Array of connected complaint records).
* **Status Codes**:
  * `200 OK`: Connected complaints retrieved.
  * `404 Not Found`: Target entity not found (`GraphEntityNotFoundError`).

### `GET /api/v1/graph/entity/{value}/risk`
* **Purpose**: Calculate topological risk assessment metrics for an entity based on degree centrality and connected complaint volume.
* **Path Parameters**:
  * `value` (*string*): Target entity value.
* **Response Model**: `EntityRiskResponse` (Calculated risk score, incident count, degree centrality, and entity label breakdowns).
* **Status Code**: `200 OK`.

### `GET /api/v1/graph/entity/{value}/ring`
* **Purpose**: Perform variable-length path traversal (`[*0..6]`) to discover the complete interconnected fraud ring component containing the target entity.
* **Path Parameters**:
  * `value` (*string*): Target entity value.
* **Response Model**: `FraudRingResponse` (Full connected component nodes and relationships).
* **Status Code**: `200 OK`.

### `GET /api/v1/graph/entity/{value}/shared`
* **Purpose**: Identify all complaints that share the specified entity identifier across distinct incident reports.
* **Path Parameters**:
  * `value` (*string*): Target entity value.
* **Response Model**: `SharedEntityResponse` (Entity details and list of co-referencing complaint nodes).
* **Status Code**: `200 OK`.

### `GET /api/v1/graph/network/summary`
* **Purpose**: Retrieve global graph intelligence statistics across the entire Neo4j database.
* **Response Model**: `NetworkSummaryResponse` (Total node counts, total relationship counts, and breakdown by node label).
* **Status Code**: `200 OK`.

### `GET /api/v1/graph/network/top-risk`
* **Purpose**: Retrieve a ranked list of the highest-risk entities across the knowledge graph based on network centrality.
* **Query Parameters**:
  * `limit` (*integer*, default: `10`, range: `1`–`100`): Maximum number of top-risk entities to return.
* **Response Model**: `list[TopRiskEntityResponse]`.
* **Status Code**: `200 OK`.

### `GET /api/v1/graph/path`
* **Purpose**: Find the shortest topological path between two entities in the knowledge graph using Cypher `shortestPath`.
* **Query Parameters**:
  * `source` (*string*, required): Starting entity value.
  * `target` (*string*, required): Ending entity value.
* **Response Model**: `PathResponse` (Path existence flag, path length, ordered node sequence, and edge sequence).
* **Status Code**: `200 OK`.

---

## 6. Graph Visualization & Analytics

The visualization and analytics APIs format knowledge graph structures for frontend network graph renderers (e.g. Cytoscape.js, React Flow) and provide aggregated statistical insights.

### `GET /api/v1/graph/visualization/{node_id}`
* **Purpose**: Extract a subgraph centered on a specific node ID formatted for frontend visualization libraries.
* **Path Parameters**:
  * `node_id` (*string*): Full standardized node identifier (e.g., `phone:+919876543210` or `complaint:<uuid>`).
* **Query Parameters**:
  * `depth` (*integer*, default: `2`, range: `1`–`5`): Maximum traversal depth from the focal node.
* **Response Model**: `GraphResponse` (Frontend-ready schema containing `nodes`, `edges`, and `metadata` counts).
* **Status Codes**:
  * `200 OK`: Subgraph successfully extracted and formatted.
  * `400 Bad Request`: Invalid node identifier format or invalid query parameter (`ValueError`).
  * `404 Not Found`: No graph nodes or edges exist for the requested focal node.

### `GET /api/v1/analytics/summary`
* **Purpose**: Retrieve high-level graph analytics summary including entity distributions and density.
* **Response Model**: `GraphSummary` (Total counts, active clusters, and structural summary).
* **Status Codes**:
  * `200 OK`: Summary successfully generated.
  * `500 Internal Server Error`: Backend database query failure.

### `GET /api/v1/analytics/top-connected`
* **Purpose**: Retrieve the most connected entities across the fraud graph sorted by degree centrality.
* **Query Parameters**:
  * `limit` (*integer*, default: `10`, range: `1`–`100`): Maximum number of entities to return.
* **Response Model**: `list[TopConnectedEntity]`.
* **Status Codes**:
  * `200 OK`: Top connected entities returned.
  * `500 Internal Server Error`: Backend database query failure.

### `GET /api/v1/analytics/shared-entities`
* **Purpose**: Retrieve all fraud identifiers that are shared across multiple independent complaints.
* **Query Parameters**:
  * `minimum_complaints` (*integer*, default: `2`, minimum: `2`): Minimum threshold of complaints required to flag an entity as shared.
* **Response Model**: `list[SharedEntityAnalysis]`.
* **Status Codes**:
  * `200 OK`: Shared entity analysis generated.
  * `500 Internal Server Error`: Backend database query failure.

---

## 7. Timeline Reconstruction

The timeline engine provides chronological event sequence reconstruction for fraud investigations.

### `GET /api/v1/timeline/{entity_value}`
* **Purpose**: Reconstruct the multi-hop chronological timeline of complaints and infrastructure expansion associated with a target entity.
* **Path Parameters**:
  * `entity_value` (*string*): Target entity lookup value.
* **Response Model**: `TimelineResponse` (Chronologically sorted events, first-seen timestamps, complaint linkages, entity reuse patterns, and fraud evolution insights).
* **Status Code**: `200 OK`.

---

## 8. General & Metadata Endpoints

### `GET /api/v1/version/`
* **Purpose**: Retrieve application semantic version information.
* **Response Model**: JSON object containing the application version string.
* **Example Response**:
  ```json
  {
    "version": "0.1.0"
  }
  ```
* **Status Code**: `200 OK`.

### `GET /api/v1/auth/`
* **Purpose**: Authentication status endpoint.
* **Current Status**: **Placeholder**. Returns `{"message": "Coming soon"}`.
* **Authentication Implementation**: Authentication and authorization (such as JWT tokens, OAuth2, API keys, Bearer tokens, or session cookies) are **not implemented** in Backend v1. All endpoints are currently accessible without credentials.
* **Status Code**: `200 OK`.

---

## 9. Error Handling

SentinelGraph AI adheres to FastAPI standard error response formatting. When an error occurs, the server emits a JSON document containing a descriptive error message:

```json
{
  "detail": "Error description or diagnostic message"
}
```

### Supported HTTP Status Codes

| Status Code | Reason Category | Trigger Scenarios in Backend v1 |
| :---: | :--- | :--- |
| **`400`** | **Bad Request** | Invalid query or path parameter values (e.g. out-of-range traversal `depth` on `/api/v1/graph/visualization/{node_id}`). |
| **`404`** | **Not Found** | Requested complaint ID or target entity value does not exist in the database or knowledge graph (`GraphEntityNotFoundError`). |
| **`422`** | **Unprocessable Entity** | Pydantic request body validation failure, prompt generation failure, or LLM output schema validation error (`PromptValidationError`, `InvalidReportSchemaError`, `ReportParsingError`). |
| **`500`** | **Internal Server Error** | Unhandled internal exception or unrecoverable database query error. |
| **`502`** | **Bad Gateway** | Upstream Google Gemini LLM provider communication error or API outage (`LLMProviderError`). |
| **`503`** | **Service Unavailable** | Readiness probe failure on `GET /health/ready` when essential database dependencies are unreachable. |
| **`504`** | **Gateway Timeout** | Upstream Google Gemini LLM API call exceeded configured timeout limits (`LLMTimeoutError`). |

---

## 10. API Integration Notes

### 10.1 Base URL & Route Conventions
* **Application API Prefix**: All functional business endpoints are rooted under `/api/v1`.
* **Operational Endpoints**: Probes (`/health`, `/health/live`, `/health/ready`) and metrics (`/metrics`) are mounted at the server root.
* **Host Configuration**: Endpoints are accessed relative to the deployed server host and port (e.g., `http://localhost:8000`).

### 10.2 Request Payloads & Headers
* **Content-Type**: Endpoints accepting JSON payloads (`IncidentCreate`, `InvestigationRequest`) require the `Content-Type: application/json` header.
* **Distributed Request Tracing**:
  * Clients may pass an `X-Request-ID` header with requests.
  * If omitted, `RequestLoggingMiddleware` automatically generates a new UUID4 string.
  * The active `X-Request-ID` is returned in the response headers and bound to all server-side structured log records.

### 10.3 Interactive Documentation & Schema Exploration
The generated FastAPI documentation interfaces serve as the authoritative live contract reference:
* **Swagger UI**: [`/docs`](/docs) &mdash; Interactive browser console for executing test requests.
* **ReDoc**: [`/redoc`](/redoc) &mdash; Technical schema reference viewer.
* **OpenAPI 3.1 Schema**: [`/api/v1/openapi.json`](/api/v1/openapi.json) &mdash; Raw JSON schema for SDK generation and contract testing.

---

## 11. Active API Surface Summary

The table below summarizes all active, mounted endpoints in SentinelGraph AI Backend v1:

| Category | HTTP Method | Endpoint Path | Primary Purpose |
| :--- | :---: | :--- | :--- |
| **Health** | `GET` | `/health` | Diagnostic health summary (PostgreSQL, Neo4j, Gemini) |
| **Health** | `GET` | `/health/live` | Process liveness probe |
| **Health** | `GET` | `/health/ready` | Ingress traffic readiness probe |
| **Observability** | `GET` | `/metrics` | Prometheus metrics scrape target |
| **Complaints** | `POST` | `/api/v1/complaints/` | Submit a new fraud complaint |
| **Complaints** | `GET` | `/api/v1/complaints/` | List complaints (paginated) |
| **Complaints** | `GET` | `/api/v1/complaints/{incident_id}` | Retrieve complaint by UUID |
| **Investigation** | `POST` | `/api/v1/investigation/` | Graph-RAG evidence aggregation |
| **Investigation** | `POST` | `/api/v1/investigation/report` | Deterministic XAI structured investigation report |
| **Graph** | `GET` | `/api/v1/graph/entity/{value}` | Retrieve entity node properties |
| **Graph** | `GET` | `/api/v1/graph/entity/{value}/neighbors` | 1-hop bidirectional neighbor expansion |
| **Graph** | `GET` | `/api/v1/graph/entity/{value}/incidents` | Connected complaint records |
| **Graph** | `GET` | `/api/v1/graph/entity/{value}/risk` | Topological risk assessment |
| **Graph** | `GET` | `/api/v1/graph/entity/{value}/ring` | Multi-hop connected fraud ring (`[*0..6]`) |
| **Graph** | `GET` | `/api/v1/graph/entity/{value}/shared` | Complaints sharing this identifier |
| **Graph** | `GET` | `/api/v1/graph/network/summary` | Global graph node and relationship counts |
| **Graph** | `GET` | `/api/v1/graph/network/top-risk` | Centrality-ranked top risk entities |
| **Graph** | `GET` | `/api/v1/graph/path` | Shortest path between two entities |
| **Visualization** | `GET` | `/api/v1/graph/visualization/{node_id}` | Subgraph extraction for Cytoscape.js / React Flow |
| **Analytics** | `GET` | `/api/v1/analytics/summary` | Overall graph analytics summary |
| **Analytics** | `GET` | `/api/v1/analytics/top-connected` | Entities with highest connectivity |
| **Analytics** | `GET` | `/api/v1/analytics/shared-entities` | Entities shared across $\ge N$ complaints |
| **Timeline** | `GET` | `/api/v1/timeline/{entity_value}` | Chronological timeline reconstruction |
| **Metadata** | `GET` | `/api/v1/version/` | Application semantic version |
| **Metadata** | `GET` | `/api/v1/auth/` | Authentication placeholder (`"Coming soon"`) |

---

## 12. Legacy & Unmounted Routes

The repository contains historical route files located in the `backend/app/api/routes/` subpackage:
* `backend/app/api/routes/graph.py`
* `backend/app/api/routes/health.py`
* `backend/app/api/routes/incidents.py`

> **Note**: These files are **unmounted legacy modules** from early sprint refactorings. They are neither imported nor mounted in `backend/app/main.py` or `backend/app/api/router.py`. They are intentionally excluded from the active API surface.

---

## 13. Related Documentation

* [`README.md`](../README.md): Project overview, quickstart instructions, and system capabilities.
* [`docs/ARCHITECTURE.md`](ARCHITECTURE.md): Full system architecture specification, middleware pipeline, and containerization.
* [`docs/DATABASE.md`](DATABASE.md): Dual-database architecture, relational schema, and Neo4j graph model.
* [`docs/CHANGELOG.md`](CHANGELOG.md): Complete chronological record of sprint milestones (Sprints 1–11).
* [`docs/ROADMAP.md`](ROADMAP.md): Product and engineering horizons (Completed v1, Near-Term Hardening, Future V2+).
* [`docs/AI_ARCHITECTURE.md`](AI_ARCHITECTURE.md): Deterministic Explainable AI (XAI) pipeline and reliability evaluation suite.

### Interactive Application Endpoints
* **Swagger UI Documentation**: [`/docs`](/docs)
* **ReDoc Technical Interface**: [`/redoc`](/redoc)
* **OpenAPI Schema Definition**: [`/api/v1/openapi.json`](/api/v1/openapi.json)
