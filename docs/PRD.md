# SentinelGraph AI: Product Requirements Document

## 1. Product Overview

**SentinelGraph AI** is an asynchronous backend platform engineered for fraud investigation and digital public safety. It combines relational persistence, labeled property graph intelligence, deterministic Explainable AI (XAI) analysis, and Large Language Model (LLM) report synthesis.

The platform architecture is grounded in the following core components:
* **Asynchronous Web Foundation**: A Python FastAPI backend providing asynchronous request processing and structured data contracts.
* **Transactional Persistence (PostgreSQL)**: Serves as the authoritative system of record for raw complaint narratives, intake metadata, triage state, and audit logs.
* **Fraud Intelligence Knowledge Graph (Neo4j AuraDB)**: Models extracted fraud identifiers and evaluates multi-hop network topologies, fraud rings, and co-occurrence patterns.
* **AI Entity Extraction & Report Synthesis (Google Gemini)**: Extracts structured fraud identifiers from unstructured complaint text and formats verified findings into standardized investigation dossiers.
* **Deterministic Explainable AI (XAI) Engine**: Executes 100% of the analytical investigation reasoning, timeline reconstruction, fraud evolution modeling, and confidence evaluation within deterministic backend services before engaging the LLM.
* **Graph Retrieval-Augmented Generation (Graph-RAG)**: Retrieves multi-hop topological graph evidence to ground investigation summaries.
* **Enterprise Observability & Health**: Features modular dependency health probes (`/health`, `/health/live`, `/health/ready`), distributed `X-Request-ID` tracing, and Prometheus metrics exposition (`/metrics`).

---

## 2. Problem Statement

Digital financial fraud and cybercrime schemes (e.g., digital arrest scams, UPI phishing, identity theft, investment fraud) generate large volumes of fragmented, unstructured complaint reports. Traditional record-oriented storage systems and investigation workflows face critical bottlenecks:

1. **Fragmented Identifier Data**: Fraud complaints contain crucial identifiers (phone numbers, UPI IDs, bank account numbers, email addresses, URLs, organizations, person names, and locations) buried within unstructured text.
2. **Hidden Multi-Hop Connections**: Fraud syndicates reuse financial and communication infrastructure across disparate incidents. Traditional relational databases make discovering multi-hop links and closed loops across shared identifiers computationally intensive.
3. **Opaque & Unverifiable AI Reasoning**: Relying on unconstrained Large Language Models to perform fraud analysis introduces risks of hallucinated links, non-reproducible risk scores, and ungrounded recommendations.
4. **Investigation Friction**: Investigators require verifiable, evidence-grounded dossiers that clearly cite specific complaints, timestamps, and confidence scores rather than opaque summaries.

SentinelGraph AI resolves these challenges by combining relational durability, property graph link analysis, deterministic evidence synthesis, and constrained LLM report generation.

---

## 3. Target Users

SentinelGraph AI Backend v1 is designed for two primary user groups:

### 3.1 Primary Users: Fraud & Cybercrime Investigators
* **Role**: Law enforcement analysts, cyber cell officers, and financial fraud investigators.
* **Needs**: Rapid identification of connected fraud networks, discovery of shared payment and communication infrastructure across complaints, and generation of evidence-grounded investigation reports with explicit citation trails.

### 3.2 Secondary Users: Engineering & Operations Teams
* **Role**: Platform engineers, DevOps specialists, and site reliability engineers (SREs).
* **Needs**: Structured request correlation (`X-Request-ID`), dependency health diagnostics (`/health/ready`), Prometheus metric scrape endpoints (`/metrics`), and containerized runtime infrastructure.

---

## 4. Product Goals (Backend v1)

The Backend v1 milestone satisfies the following core functional and technical goals:

1. **Reliable Complaint Ingestion**: Ingest and durably persist structured complaint records in PostgreSQL with transactional guarantees.
2. **Automated AI Entity Extraction**: Extract standardized fraud entities (`Phone`, `UPI`, `Email`, `URL`, `BankAccount`, `Organization`, `Person`, `Location`) from unstructured narratives using Google Gemini.
3. **Knowledge Graph Construction**: Build and maintain an idempotent Neo4j fraud knowledge graph connecting complaints to extracted entities.
4. **Topological Relationship Analysis**: Discover multi-hop connections, variable-length fraud rings (`[*0..6]`), and shared identifiers across distinct complaints.
5. **Timeline & Evolution Reconstruction**: Reconstruct chronological event sequences and detect payment/communication infrastructure expansion patterns.
6. **Evidence-Grounded Intelligence**: Generate structured investigation evidence with deterministic confidence scoring (`0.0 <= confidence <= 1.0`) and severity ratings.
7. **Strict Explainable AI (XAI)**: Maintain 100% deterministic backend ownership of analytical reasoning, scoring, and graph traversals.
8. **Constrained Report Synthesis**: Utilize Gemini strictly as a structured report writer translating verified case files into formal dossiers with prompt fingerprinting (`prompt_hash`) and citation preservation.
9. **Comprehensive Observability**: Expose granular dependency health probes, distributed request tracing, and Prometheus metrics for HTTP traffic and LLM token usage.
10. **Tested & Containerized Foundation**: Deliver a tested, containerized backend foundation with multi-stage Docker builds, Docker Compose orchestration, and automated CI quality checks.

---

## 5. Non-Goals for Backend v1

The following capabilities are explicitly out of scope for the Backend v1 milestone and represent future roadmap horizons:

* **Investigator Web Frontend**: No graphical user interface (web dashboard) is included in Backend v1; all capabilities are exposed via REST APIs.
* **Multimodal Voice Scam Processing**: No audio ingestion, speech recognition, or acoustic stress analysis is implemented in v1.
* **Counterfeit Document & Image OCR**: No visual analysis of forged notices, fake warrants, or payment screenshots is implemented in v1.
* **Multilingual & Regional Dialect Translation**: Ingestion and entity extraction in regional Indian languages are not implemented in v1.
* **Direct Banking Transaction Controls**: No direct webhooks or automated fund-freezing integration with banking switches is implemented in v1.
* **External Law Enforcement Portal Connectors**: No direct API integration with the National Cyber Crime Reporting Portal (NCRP) or state police databases is implemented in v1.
* **Multi-Provider LLM Adapters**: No concrete adapters for Anthropic Claude, OpenAI, or local open-weights models are implemented in v1 (Google Gemini is the active provider).
* **Distributed Transactions & Event Streaming**: No distributed Two-Phase Commit (2PC), Kafka/RabbitMQ brokers, or Outbox/CDC pipelines exist in v1.
* **Real-Time Push Alerting**: No WebSocket or Server-Sent Events (SSE) live notification streaming is implemented in v1.

---

## 6. Functional Requirements

### 6.1 Complaint Intake & Persistence
* **Submission Ingestion**: The system shall accept structured fraud complaint submissions via the `POST /api/v1/complaints/` API endpoint.
* **Schema Validation**: The system shall validate incoming request payloads against the `IncidentCreate` Pydantic model.
* **Relational Persistence**: The system shall durably persist validated complaint records in the PostgreSQL `incidents` table.
* **Identity & Timestamps**: The system shall assign and maintain immutable UUID primary keys (`id`), creation timestamps (`created_at`), and status fields.
* **Complaint Queries**: The system shall expose paginated listing (`GET /api/v1/complaints/`) and individual record retrieval (`GET /api/v1/complaints/{incident_id}`).

### 6.2 AI Entity Extraction
* **Automated Extraction**: The system shall analyze unstructured complaint narratives using Google Gemini (`gemini-1.5-pro` / `gemini-1.5-flash`) to extract relevant fraud identifiers.
* **Supported Entity Categories**: The extraction pipeline shall extract entities across 8 standardized categories:
  * `Phone`: Telephone and mobile numbers.
  * `UPI`: Unified Payments Interface virtual payment addresses (VPAs).
  * `Email`: Email addresses.
  * `URL`: Phishing, fraudulent, or impersonation web links.
  * `BankAccount`: Bank account numbers.
  * `Organization`: Impersonated or involved business and institutional entities.
  * `Person`: Suspect names, aliases, or caller identities.
  * `Location`: Physical addresses, cities, or geographic references.
* **Downstream Delivery**: The extraction pipeline shall normalize and deliver structured entity objects to the graph ingestion service.
* **Reasoning Boundary**: Entity extraction shall be strictly confined to identifying named entities and values from text; Gemini shall not perform graph or fraud investigation reasoning.

### 6.3 Knowledge Graph Construction
* **Property Graph Representation**: The system shall ingest complaints and extracted entities into the Neo4j AuraDB property graph.
* **Deterministic Graph Identifiers**: Graph nodes shall use deterministic identity strings:
  * Complaint nodes: `complaint:<incident_id>`
  * Entity nodes: `<category_lower>:<normalized_value>` (e.g., `phone:+919876543210`, `upi:fraud@okhdfcbank`).
* **Graph Relationship Topology**: The system shall persist the single canonical relationship type connecting complaints to entities:
  ```text
  (:Complaint)-[:MENTIONS]->(:Entity)
  ```
  *(Note: `REPORTED_IN`, `ASSOCIATED_WITH`, and `TRANSFERRED_TO` are not persisted relationships).*
* **Idempotent Ingestion**: Graph writes shall use application-level Cypher `MERGE` patterns to guarantee idempotent node and edge creation without duplicating entities across multiple complaint mentions.

### 6.4 Graph Investigation & Link Analysis
The system shall expose graph analytics endpoints to query topological structures in Neo4j:
* **Entity Lookup**: Retrieve node attributes and confidence scores (`GET /api/v1/graph/entity/{value}`).
* **1-Hop Neighbor Expansion**: Retrieve directly connected neighbor nodes (`GET /api/v1/graph/entity/{value}/neighbors`).
* **Connected Complaints**: Retrieve all complaints referencing a specific entity (`GET /api/v1/graph/entity/{value}/incidents`).
* **Shared Entity Analysis**: Identify entities referenced across multiple independent complaints (`GET /api/v1/graph/entity/{value}/shared` and `GET /api/v1/analytics/shared-entities`).
* **Fraud Ring Discovery**: Traverse variable-length multi-hop paths (`[*0..6]`) to discover connected fraud ring components (`GET /api/v1/graph/entity/{value}/ring`).
* **Shortest Path Analysis**: Discover shortest topological paths between two entities via Cypher `shortestPath` (`GET /api/v1/graph/path`).
* **Network Summaries**: Expose global graph node and edge counts (`GET /api/v1/graph/network/summary` and `GET /api/v1/analytics/summary`).
* **Risk & Centrality Ranking**: Rank entities by topological risk and degree centrality (`GET /api/v1/graph/network/top-risk` and `GET /api/v1/analytics/top-connected`).

### 6.5 Timeline Reconstruction & Fraud Evolution
* **Chronological Sequence Reconstruction**: The system shall reconstruct ordered chronological event histories of connected complaints for a target entity (`GET /api/v1/timeline/{entity_value}`).
* **Evidence Aggregation**: The timeline engine shall aggregate complaint timestamps, reporter types, and incident categories.
* **Infrastructure Evolution Tracking**: The system shall identify the chronological introduction and reuse of payment/communication infrastructure (e.g. initial phone contact followed by secondary UPI and mule bank accounts).
* **Deterministic Confidence Evaluation**: The system shall assign deterministic confidence scores (`0.0 <= confidence <= 1.0`) grounded in evidentiary density and relationship proximity.

### 6.6 Investigation & Explainable AI (XAI) Report Generation
* **Multi-Hop Evidence Collection**: The system shall gather multi-hop graph evidence and timeline context for target entities.
* **Deterministic Investigation Boundary**: Core investigative reasoning, risk scoring, evidence correlation, and timeline sequencing shall be executed entirely by deterministic backend Python services (*InvestigationSummaryService, TimelineService, EntityAnalysisService, FraudEvolutionService, EvidenceEngine*).
* **Citation Preservation**: The system shall map and preserve explicit evidence citations (`[Complaint: <id>]`) throughout the analysis pipeline.
* **Constrained Report Synthesis**: The system shall use Google Gemini strictly as a report writer to translate deterministic context into a structured `ProfessionalInvestigationReport`.
* **Prompt Fingerprinting**: The system shall compute a SHA-256 fingerprint (`prompt_hash`) for each constructed investigation prompt to ensure auditability and prompt consistency.

### 6.7 Observability & Telemetry
* **Dependency Health Probes**: The system shall provide diagnostic dependency checks (`GET /health`) covering PostgreSQL, Neo4j AuraDB, and Gemini API readiness.
* **Liveness & Readiness**: The system shall provide orchestrator liveness (`GET /health/live`) and load balancer readiness (`GET /health/ready`) probes.
* **Distributed Request Correlation**: The system shall propagate or generate an `X-Request-ID` across all HTTP transactions and inject it into response headers.
* **Structured Contextual Logging**: The system shall bind `X-Request-ID` to Loguru async execution context (`ContextVar`) for end-to-end log correlation.
* **HTTP Prometheus Metrics**: The system shall track HTTP request counts (`http_requests_total`) and request latencies (`http_request_duration_seconds`).
* **LLM Telemetry Metrics**: The system shall expose Prometheus metrics for LLM calls (`llm_requests_total`), call latencies (`llm_request_duration_seconds`), and token consumption (`llm_tokens_total`).

---

## 7. Quality & Reliability Requirements

### 7.1 Automated Testing & Code Quality
* **Pytest Test Suite**: The backend shall maintain comprehensive automated unit, integration, and service tests executed via `pytest`.
* **Async Test Execution**: Asynchronous coroutines, database sessions, and API endpoints shall be tested using `pytest-asyncio`.
* **Static Analysis & Linting**: Code quality, formatting, and import conventions shall be enforced via `ruff check` and `ruff format`.
* **Continuous Integration**: A multi-stage GitHub Actions CI workflow (`.github/workflows/ci.yml`) shall automatically execute linting, code formatting checks, and the full pytest suite on every push and pull request.

### 7.2 Error Isolation & Failure Resilience
* **Durable Relational Baseline**: PostgreSQL provides the transactional system of record for all complaint submissions.
* **Explicit Downstream Failure Handling**: Failures occurring during asynchronous Gemini entity extraction or Neo4j graph ingestion shall be trapped, logged, and isolated.
* **Independent Failure Domain**: Downstream AI or graph failures shall not retroactively roll back the already committed PostgreSQL complaint record, guaranteeing that reported incidents are never lost due to external API or graph outages.
* **Domain Exception Mapping**: Explicit exceptions (`GraphEntityNotFoundError`, `PromptValidationError`, `LLMProviderError`, `LLMTimeoutError`) shall map cleanly to standard HTTP status codes (`400`, `404`, `422`, `502`, `504`).

### 7.3 Data Consistency & Idempotency
* **Application-Level Idempotency**: Neo4j graph ingestion shall employ application-level Cypher `MERGE` patterns on deterministic node identifiers to prevent duplicate graph entities during retried ingestion runs.
* **Dual-Database Coordination**: System design acknowledges dual-database architecture constraints (PostgreSQL + Neo4j AuraDB) without making unsubstantiated claims of distributed Two-Phase Commit (2PC) or CDC pipelines.

---

## 8. Architectural Boundaries

### 8.1 Relational vs. Graph Responsibilities
* **PostgreSQL Responsibilities**: Authoritative transactional system of record for complaint records, narrative bodies, intake metadata, triage state, and audit logs.
* **Neo4j AuraDB Responsibilities**: Dedicated knowledge graph for entity link analysis, multi-hop relationship traversals, fraud ring discovery, and topological centrality metrics.
* **Application Orchestration**: The backend application layer coordinates the dual-database data flow without relying on a distributed transaction coordinator (2PC), maintaining decoupled database operational lifecycles.

### 8.2 Deterministic Reasoning Boundary
* **Backend Ownership**: 100% of analytical investigation logic, evidence correlation, timeline reconstruction, and topological risk scoring is executed by deterministic backend Python services.
* **Non-Autonomous LLM**: Google Gemini does not independently formulate investigative hypotheses, compute risk scores, or assert unverified relationships.
* **Role of LLM**: Google Gemini is constrained to two specific pipelines: (1) unstructured entity extraction, and (2) structured formatting and stylistic synthesis of pre-verified case files into legal-grade dossiers.

### 8.3 API Boundary
* **REST Interface**: Public functionality is exposed as an asynchronous HTTP REST API via FastAPI.
* **Prefix Isolation**: All functional application endpoints are isolated under the `/api/v1` prefix.
* **Root Operational Probes**: Dependency health probes (`/health`, `/health/live`, `/health/ready`) and Prometheus metrics (`/metrics`) are hosted at the root for standard infrastructure integration.
* **Authentication Boundary**: Authentication and authorization are out of scope for Backend v1; the `/api/v1/auth/` endpoint is a placeholder.

### 8.4 Deployment Boundary
* **Containerization Baseline**: The backend is packaged using a multi-stage Dockerfile adhering to non-root execution practices (`appuser`).
* **Local & Integrated Orchestration**: Multi-container testing and local environments are managed via Docker Compose (`docker-compose.yml`).
* **Continuous Integration**: Code formatting, linting, and automated test execution are automated via GitHub Actions CI (`.github/workflows/ci.yml`).
* **Scope Boundary**: Active cloud deployments (e.g., Railway, Vercel, AWS, GCP, Azure) are not part of the core repository baseline and are designated for future infrastructure hardening.

---

## 9. Success Criteria (Backend v1)

The completion of SentinelGraph AI Backend v1 is evaluated against the following grounded, measurable criteria:

1. **Transactional Ingestion**: The complaint intake API (`POST /api/v1/complaints/`) and retrieval APIs operate reliably against PostgreSQL with valid schema contracts.
2. **Entity Extraction & Ingestion**: Supported fraud entities are extracted from narratives via Gemini and represented idempotently in Neo4j AuraDB.
3. **Graph Link Analysis**: Graph queries successfully identify shared identifiers, connected complaint clusters, and multi-hop fraud rings (`[*0..6]`).
4. **Timeline & Evolution Tracking**: Chronological timelines and infrastructure evolution summaries are generated deterministically from graph evidence.
5. **Evidentiary Citation Grounding**: Generated investigation dossiers preserve explicit complaint citations (`[Complaint: <id>]`) mapped directly to verified source records.
6. **Deterministic Reasoning Integrity**: All fraud risk calculations and relationship traversals remain fully deterministic and backend-owned.
7. **Telemetry & Observability**: Prometheus metrics accurately track HTTP request traffic and LLM call volume, durations, and token usage.
8. **Dependency Health Diagnostics**: Modular health endpoints (`/health`, `/health/live`, `/health/ready`) accurately report dependency states and return appropriate status codes.
9. **Automated Quality Gates**: The automated test suite and Ruff static analysis pass consistently within the GitHub Actions CI pipeline.
10. **Containerized Execution**: The backend builds cleanly as a lightweight container image and runs successfully within Docker Compose environments.
11. **Architectural Specification**: Core system architecture, dual-database boundaries, and XAI pipelines are documented across dedicated technical references.
12. **Public API Contract**: The API surface is fully documented in `docs/API.md` and remains consistent with the live OpenAPI 3.1 specification.

---

## 10. Risks & Known Constraints

### 10.1 Dual-Database Consistency
* **Sequence of Writes**: PostgreSQL commits complaint records before initiating asynchronous Gemini extraction and Neo4j graph writes.
* **Partial Ingestion Risk**: Transient AI API or Neo4j outages may leave graph state incomplete relative to the relational database.
* **No Distributed 2PC**: The system does not implement distributed Two-Phase Commit, Transactional Outbox, or CDC pipelines.
* **Rebuild Utility**: Graph consistency can be restored from the PostgreSQL source of truth using the built-in graph rebuild service.

### 10.2 LLM Dependency & Fallbacks
* **Provider Dependency**: Entity extraction and report synthesis depend on upstream Google Gemini API availability.
* **Failure Isolation**: Upstream timeouts and API errors are trapped and mapped to standard HTTP `502 Bad Gateway` and `504 Gateway Timeout` responses.
* **Single-Provider Architecture**: Multi-provider LLM adapters (e.g., Anthropic Claude, OpenAI, local models) represent future roadmap capabilities rather than current functionality.

### 10.3 Graph Schema Hardening
* **Application-Level Merge**: Neo4j node and relationship uniqueness currently relies on application-level Cypher `MERGE` patterns.
* **Constraint Gaps**: Database-level uniqueness constraints and property indexes are not yet enforced in the active Neo4j database, representing near-term hardening opportunities.

### 10.4 Observability Infrastructure
* **Metrics Exposition**: The backend exposes raw Prometheus metrics via `/metrics`.
* **Dashboarding & Alerting**: Production Grafana dashboards and Alertmanager rules are not implemented in Backend v1 and remain future operational tasks.

### 10.5 Authentication & Access Control
* **No Auth Implementation**: Backend v1 does not implement user authentication, API keys, or role-based access control (RBAC).
* **Placeholder Endpoint**: The `/api/v1/auth/` endpoint returns a static placeholder response (`{"message": "Coming soon"}`).

---

## 11. Future Product Direction

> **Note**: The items below represent strategic roadmap horizons and are **not** Backend v1 requirements or implemented capabilities.

1. **Multimodal Scam Intelligence**: Expanding ingestion to process scam audio recordings, call transcripts, forged documents, and screenshot OCR.
2. **Interactive Investigator Web Platform**: Developing a modern frontend workspace with interactive Cytoscape.js / React Flow network graphs, timeline visualizers, and dossier export tools.
3. **Multilingual & Regional Processing**: Supporting complaint ingestion and entity extraction across major Indian regional languages and mixed-language dialects (e.g., Hinglish).
4. **Law Enforcement & Financial Integrations**: Direct connector integrations with the National Cyber Crime Reporting Portal (NCRP), state police portals, and banking transaction switches.
5. **Multi-Provider LLM & Self-Hosted Models**: Provider-agnostic LLM abstraction layer supporting Anthropic Claude, OpenAI, and self-hosted open-weights models (e.g., Llama 3).
6. **Advanced Graph Machine Learning**: Implementing Graph Neural Networks (GNNs), community detection algorithms (Louvain/Leiden), and automated mule account link prediction.

---

## 12. Requirements Traceability

The table below maps core product requirements to their backend implementation modules and primary technical documentation:

| Requirement Area | Backend Implementation | Primary Documentation |
| :--- | :--- | :--- |
| **Complaint Persistence** | PostgreSQL + `IncidentRepository` / `IncidentService` | [`DATABASE.md`](DATABASE.md) |
| **Fraud Graph Intelligence** | Neo4j AuraDB + `GraphRepository` / `GraphQueryService` | [`DATABASE.md`](DATABASE.md) |
| **Deterministic Investigation** | Deterministic XAI Services (*Timeline, Entity, Evolution, Evidence*) | [`AI_ARCHITECTURE.md`](AI_ARCHITECTURE.md) |
| **Report Generation** | `LLMClient` + `InvestigationReportService` + `ReportParser` | [`AI_ARCHITECTURE.md`](AI_ARCHITECTURE.md) |
| **Public API Surface** | FastAPI Routers (`/api/v1/*`) | [`API.md`](API.md) |
| **System Architecture** | Application Core + Dependency Injection Topology | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| **Observability & Health** | Health Diagnostics + `X-Request-ID` + Prometheus | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| **Project Evolution** | Sprint Milestones (Sprints 1–11) | [`CHANGELOG.md`](CHANGELOG.md) |
| **Product Direction** | Backend v1 Completion & Horizons 2–3 | [`ROADMAP.md`](ROADMAP.md) |

---

## 13. Related Documentation

* [`README.md`](../README.md): High-level system overview, setup instructions, and quickstart guide.
* [`docs/ARCHITECTURE.md`](ARCHITECTURE.md): Complete backend architecture, dependency injection, and middleware specification.
* [`docs/DATABASE.md`](DATABASE.md): Relational schema definitions, Neo4j graph model, and dual-database design.
* [`docs/API.md`](API.md): Comprehensive REST API endpoint reference, parameters, and error catalog.
* [`docs/CHANGELOG.md`](CHANGELOG.md): Historical record of engineering sprints and documentation releases.
* [`docs/ROADMAP.md`](ROADMAP.md): Product and engineering strategic horizons across Completed v1, Near-Term Hardening, and Future V2+.
* [`docs/AI_ARCHITECTURE.md`](AI_ARCHITECTURE.md): Technical specification of the deterministic XAI pipeline, prompt engineering, and evaluation suite.
