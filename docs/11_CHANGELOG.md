# 📜 SentinelGraph AI: Project Changelog

All notable development changes, architectural additions, and sprint milestones for SentinelGraph AI are documented in this file.

---

## [1.1.0] - 2026-09-07

### Release Overview: Full-Stack Productionization & Frontend Milestone
Major milestone transforming SentinelGraph AI from a backend-only prototype into a complete, containerized full-stack fraud intelligence platform. Adds an interactive React 18 analyst console with Cytoscape.js topological visualization, a dedicated AI Governance Console, an enterprise Prometheus & Grafana observability stack with 5 alert rules, database unique constraints on case references, programmatic Neo4j DDL uniqueness constraints, and unified Docker Compose orchestration on port 80.

---

### Sprint 12: Production Hardening, Observability Stack & Frontend Implementation (2026-08-27 – 2026-09-07)

#### Database Schema & Graph Constraint Hardening (2026-08-27)
* **Alembic Migration Revision 2 (`e7c2a19d4b8f`)**: Authored and applied migration adding `uq_incidents_case_reference` uniqueness constraint to `incidents(case_reference)`, guaranteeing that external police FIRs and bank dispute references remain unique across the relational system of record.
* **Neo4j DDL Uniqueness Constraints**: Implemented programmatic schema initialization in [`app/db/neo4j_schema.py`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/db/neo4j_schema.py) executing 9 database-level uniqueness constraints on application startup (`CREATE CONSTRAINT uq_<label>_id IF NOT EXISTS FOR (n:<Label>) REQUIRE n.id IS UNIQUE`) across all persisted node labels.

#### LLM Reliability & Diagnostic Hardening (2026-08-28)
* **Gemini Client Bounded Retries**: Hardened [`GeminiClient`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/ai/client.py) with exponential backoff for transient provider failures (HTTP 429, 5xx, `ServerError`).
* **Non-Blocking Threadpool Execution**: Offloaded synchronous SDK calls to worker threads via `asyncio.to_thread` with strict per-attempt timeout enforcement via `asyncio.wait_for`.
* **Logging Redaction & Masking**: Sanitized debug logs to prevent leaking sensitive investigation target values and PII.
* **Transaction Rollback Resilience**: Hardened SQLAlchemy async transaction boundaries to guarantee clean rollbacks upon unexpected exceptions.

#### Observability Stack & Container Verification (2026-08-30)
* **Prometheus Alert Rules**: Created [`monitoring/prometheus/alerts.yml`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/monitoring/prometheus/alerts.yml) defining 5 production alerting rules (`HighHttp5xxErrorRate`, `ElevatedHttpRequestLatency`, `ReadinessProbeFailing`, `HighLlmErrorRate`, `ElevatedLlmRequestLatency`).
* **Grafana Operational Dashboard**: Authored pre-provisioned Grafana operations dashboard [`monitoring/grafana/dashboards/sentinelgraph-operations.json`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/monitoring/grafana/dashboards/sentinelgraph-operations.json) visualizing API throughput, p50/p95/p99 latency quantiles, token consumption, and dependency health.
* **Credential Safety**: Migrated database and Gemini passwords to Pydantic `SecretStr` to eliminate plaintext exposure in string representations.
* **CI Migration Verification Gate**: Updated GitHub Actions workflow ([`.github/workflows/ci.yml`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/.github/workflows/ci.yml)) to run dry-run Alembic migration verification (`alembic upgrade head --sql`) before executing pytest.

#### React 18 Web Application & Analyst Console (2026-09-03 – 2026-09-04)
* **Single Page Application Setup**: Initialized React 18, TypeScript, Vite, Tailwind CSS, and Lucide React under `frontend/`.
* **Risk Overview Page**: Built `#risk-overview` dashboard featuring global fraud KPIs, top connected entity tables, shared infrastructure hubs, and recent complaints.
* **Cytoscape.js Network Graph**: Built interactive topological graph component with switchable physics layouts (`cose`, `concentric`, `breadthfirst`), 1–5 hop depth slider, pan/zoom controls, and node detail drawer.
* **Investigation Timeline**: Built chronological event visualization tracing multi-hop complaint progression and infrastructure expansion.
* **AI Investigation Dossier**: Built structured report viewer rendering verified findings, confidence scores, actionable containment recommendations, and citation trails.
* **AI Governance & Guardrails Console**: Built `#evaluation` page explaining the 3-Layer Guardrail Architecture, 5 Golden Scenario specifications, evaluation dimension formulas, and live Prometheus telemetry.

#### Full-Stack Docker & Cloud Deployment (2026-09-05 – 2026-09-07)
* **Frontend Nginx Dockerfile**: Created multi-stage build (`node:20-alpine` builder, `nginx:alpine` runner) serving static assets and reverse-proxying `/api/`, `/health`, and `/metrics` to `http://api:8000`.
* **Root Unified Docker Compose**: Orchestrated the complete platform stack (frontend on port 80, backend on port 8000, PostgreSQL 16, Neo4j 5.26, Prometheus, and Grafana) with automated container healthchecks.
* **Render & Managed Cloud Readiness**: Enhanced [`backend/entrypoint.sh`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/entrypoint.sh) to bind dynamically to `$PORT` and auto-execute `alembic upgrade head` when `RUN_MIGRATIONS=true`.

---

## [1.0.0] - 2026-08-26

### Release Overview: Backend v1 Milestone
Initial backend v1 release establishing the dual-database architecture, deterministic Explainable AI (XAI) pipeline, Google Gemini integration, and offline evaluation suite.

---

### Sprint 1: Project Foundation & Configuration (2026-06-28 – 2026-06-29)
* **Configuration**: Implemented centralized typed application configuration using `pydantic-settings` (`Settings` class).
* **Logging**: Integrated structured application logging with Loguru (`logger`).
* **Application Entrypoint**: Initialized the core FastAPI application lifecycle, middleware foundation, and API router.

### Sprint 2: PostgreSQL Relational Infrastructure (2026-06-30 – 2026-07-07)
* **Async Engine**: Configured SQLAlchemy 2.0 async engine using `asyncpg` with connection pooling (`DB_POOL_SIZE=10`, `DB_MAX_OVERFLOW=20`).
* **Model Layer**: Created declarative `Base`, reusable `UUIDMixin` and `TimestampMixin`, and the core `Incident` ORM model for the `incidents` table.
* **Schema & Enums**: Defined PostgreSQL ENUM types for incident status, priority, reporter type, source, and scam category, along with risk score range check constraints.
* **Alembic Migrations**: Configured Alembic with synchronous `psycopg2` driver support and authored baseline migration (`3d3cf359c2a1_create_incidents_table.py`).

### Sprint 3: Persistence Layer & Incident API (2026-07-08 – 2026-07-10)
* **Repository Architecture**: Implemented generic `BaseRepository` and specialized `IncidentRepository` with domain-specific filtering, pagination, and keyword search.
* **Service Layer**: Implemented `BaseService` and `IncidentService` with explicit session transaction boundaries (`commit` and `rollback`).
* **REST Endpoints**: Created public complaint ingestion and retrieval endpoints (`/api/v1/complaints`).

### Sprint 4: AI Entity Extraction & Neo4j Ingestion (2026-07-11 – 2026-07-15)
* **AI Extraction**: Integrated Google Gemini via `EntityExtractionService` to extract standardized fraud identifiers (`Phone`, `UPI`, `Email`, `URL`, `BankAccount`, `Organization`, `Person`, `Location`).
* **Graph Driver**: Implemented lifecycle connection management for the Neo4j async driver (`AsyncGraphDatabase`).
* **Graph Model**: Implemented `GraphBuilder` and `GraphRepository` utilizing atomic Cypher `MERGE` transactions with deterministic node ID prefixes.
* **Relationship Topology**: Established the single persisted `MENTIONS` relationship type (`(:Complaint)-[:MENTIONS]->(:Entity)`).
* **Ingestion Pipeline**: Created `IncidentProcessingService` coordinating post-commit AI extraction and graph persistence with decoupled error isolation.

### Sprint 5: Graph Intelligence & Topological Analytics (2026-07-17 – 2026-07-18)
* **Fraud Ring Detection**: Implemented variable-length path expansion (`[*0..6]`) to identify connected fraud ring components (`find_fraud_ring`).
* **Network Statistics**: Created network-wide intelligence query calculating node and relationship distributions (`get_network_summary`).
* **Risk Scoring**: Developed graph-based risk metric evaluation and entity risk scoring (`_calculate_risk`, `get_top_risk_entities`).
* **Shortest Path Analysis**: Implemented shortest connection path traversal between graph entities (`find_shortest_path`).
* **Shared Entity Analysis**: Implemented cross-complaint shared identifier correlation (`find_shared_entity`).

### Sprint 6: Graph-RAG Investigation Engine & Caching (2026-07-18)
* **Evidence Collection**: Implemented `InvestigationService` collecting multi-hop graph context and metrics (`InvestigationEvidence`).
* **Prompt Assembly**: Created `PromptBuilder` for formatting investigation context into structured LLM prompts.
* **Report Parser**: Implemented `ReportParser` to parse and validate structured JSON responses from Gemini.
* **Investigation Cache**: Added in-memory TTL caching (`InvestigationCache`, 300s TTL) for fast repeated investigation lookups.
* **Investigation API**: Exposed the Graph-RAG pipeline via the `POST /api/v1/investigation` endpoint.

### Sprint 7: Graph Visualization Subgraph API (2026-07-19 – 2026-07-23)
* **Visualization Subsystem**: Added Cypher subgraph extraction queries (`get_subgraph`) and Cytoscape-compatible node-link schemas.
* **Visualization Endpoints**: Exposed interactive subgraph extraction endpoint (`/api/v1/graph/visualization/{node_id}`).
* **Architecture Assets**: Authored system diagrams and Swagger documentation previews.

### Sprint 8: Timeline Reconstruction & Fraud Evolution (2026-07-23 – 2026-07-29)
* **Timeline Engine**: Implemented `TimelineService` to reconstruct multi-hop chronological complaint timelines from graph linkages.
* **Entity Evolution**: Implemented `EntityAnalysisService` tracking entity lifecycle, first-seen timestamps, and cross-complaint reuse counts.
* **Timeline Analysis**: Implemented `TimelineAnalysisService` generating deterministic chronological insights.
* **Fraud Evolution Modeling**: Implemented `FraudEvolutionService` detecting payment infrastructure and communication channel expansion events.
* **Evidence Engine**: Developed `EvidenceEngine` evaluating rule-based evidence severity and mathematical confidence scoring (`0.0 <= confidence <= 1.0`).
* **Timeline Endpoints**: Exposed chronological reconstruction endpoints (`/api/v1/timeline/{entity_value}`).

### Sprint 9 & 9.5: Deterministic XAI Pipeline & Evaluation Suite (2026-07-30 – 2026-07-31)
* **Deterministic XAI Directive**: Shifted investigation reasoning to 100% deterministic backend execution with 0% LLM reasoning dependency.
* **Case File Builder**: Implemented `InvestigationSummaryService` assembling canonical immutable investigation summary DTOs.
* **Report Context**: Implemented `ReportContextBuilder` compiling token-optimized `InvestigationReportContext` view models.
* **Prompt Fingerprinting**: Added `PromptTemplateRegistry` and `PromptBuilder` with SHA-256 prompt hashing (`prompt_hash`) for deterministic reproducibility.
* **Professional Report Contract**: Designed `ProfessionalInvestigationReport` schema with citation preservation and execution telemetry.
* **AI Evaluation Suite (Sprint 9.5)**: Implemented automated evaluation package (`app/evaluation`) including `GoldenDataset` (5 golden scenarios), `CitationVerifier`, `HallucinationDetector`, `ReportQualityEvaluator`, and `PerformanceBenchmarker`.

### Sprint 10: CI/CD Pipeline & Containerization (2026-07-31 – 2026-08-06)
* **Continuous Integration**: Configured GitHub Actions workflow (`.github/workflows/ci.yml`) automating Ruff linting and pytest suites.
* **Docker Setup**: Built production multi-stage backend `Dockerfile` with minimal non-root `appuser:10001` runner container.
* **Orchestration**: Created backend `docker-compose.yml` orchestrating FastAPI and PostgreSQL 16 with health checks.

### Sprint 11: Enterprise Health & Prometheus Observability (2026-08-16 – 2026-08-25)
* **Health Subsystem**: Implemented modular health checking subsystem (`PostgresHealthChecker`, `Neo4jHealthChecker`, `GeminiHealthChecker`, `HealthService`, `/health`, `/health/live`, `/health/ready`).
* **Distributed Tracing**: Implemented `RequestLoggingMiddleware` with `X-Request-ID` UUID4 generation, async `ContextVar` propagation, Loguru binding, and response header injection.
* **HTTP Prometheus Metrics**: Registered and observed `http_requests_total` and `http_request_duration_seconds` with parameterized route labeling.
* **LLM Prometheus Telemetry**: Implemented `llm_requests_total`, `llm_request_duration_seconds`, and `llm_tokens_total` metrics partitioned by provider, model, and token type.
* **Metrics Exposition**: Exposed default Prometheus metrics endpoint (`GET /metrics`).
