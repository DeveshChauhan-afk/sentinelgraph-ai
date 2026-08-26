# SentinelGraph AI: Project Changelog

All notable development changes, architectural additions, and sprint milestones for SentinelGraph AI are documented in this file.

## [1.0.0] - 2026-08-26

### Release Overview
Backend v1 completion milestone of SentinelGraph AI: an asynchronous FastAPI platform integrating a hybrid dual-database architecture (PostgreSQL + Neo4j AuraDB), Google Gemini entity extraction, topological fraud ring analytics, deterministic Explainable AI (XAI) report generation, an automated AI evaluation suite, enterprise Prometheus observability, and containerized deployment infrastructure.

---

### Sprint 1: Project Foundation & Configuration (2026-06-28 – 2026-06-29)
* **Configuration**: Implemented centralized typed application configuration using `pydantic-settings` (`Settings` class).
* **Logging**: Integrated structured application logging with Loguru (`logger`).
* **Application Entrypoint**: Initialized the core FastAPI application lifecycle, middleware foundation, and API router.
* **Release Baseline**: Established the initial `v0.1.0` backend foundation.

### Sprint 2: PostgreSQL Relational Infrastructure (2026-06-30 – 2026-07-07)
* **Async Engine**: Configured SQLAlchemy 2.0 async engine using `asyncpg` with connection pooling (`DB_POOL_SIZE=10`, `DB_MAX_OVERFLOW=20`).
* **Model Layer**: Created declarative `Base`, reusable `UUIDMixin` and `TimestampMixin`, and the core `Incident` ORM model for the `incidents` table.
* **Schema & Enums**: Defined PostgreSQL ENUM types for incident status, priority, reporter type, source, and scam category, along with risk score range check constraints.
* **Alembic Migrations**: Configured Alembic with synchronous `psycopg2` driver support and authored the baseline database migration (`3d3cf359c2a1_create_incidents_table.py`).

### Sprint 3: Persistence Layer & Incident API (2026-07-08 – 2026-07-10)
* **Repository Architecture**: Implemented generic `BaseRepository` and specialized `IncidentRepository` with domain-specific filtering, pagination, and keyword search.
* **Service Layer**: Implemented `BaseService` and `IncidentService` with explicit session transaction boundaries (`commit` and `rollback`).
* **REST Endpoints**: Created public complaint ingestion and retrieval endpoints (`/api/v1/complaints`).

### Sprint 4: AI Entity Extraction & Neo4j Ingestion (2026-07-11 – 2026-07-15)
* **AI Extraction**: Integrated Google Gemini via `EntityExtractionService` to extract structured fraud identifiers (`Phone`, `UPI`, `Email`, `URL`, `BankAccount`, `Organization`, `Person`, `Location`).
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

### Sprint 7: Graph Visualization & Architecture Assets (2026-07-19 – 2026-07-23)
* **Visualization Subsystem**: Added Cypher subgraph extraction queries (`get_subgraph`) and D3.js/Cytoscape formatted node-link schemas.
* **Visualization Endpoints**: Exposed interactive subgraph extraction endpoints (`/api/v1/graph/subgraph`).
* **Project Showcase Assets**: Generated high-level architecture diagrams (HLD), database views, and Swagger documentation screenshots for repository documentation.

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
* **Provider-Agnostic LLM Client**: Created abstract `LLMClient` interface and Google Gemini SDK implementation.
* **Professional Report Contract**: Designed `ProfessionalInvestigationReport` schema with citation preservation and execution telemetry.
* **AI Evaluation Suite (Sprint 9.5)**: Implemented automated evaluation package (`app/evaluation`) including `GoldenDataset`, `CitationVerifier`, `HallucinationDetector`, `ReportQualityEvaluator`, and `PerformanceBenchmarker`.

### Sprint 10: CI/CD Pipeline & Containerization (2026-07-31 – 2026-08-06)
* **Continuous Integration**: Configured GitHub Actions workflow (`.github/workflows/ci.yml`) automating Ruff linting and pytest suites.
* **Docker Setup**: Built production multi-stage `Dockerfile` with minimal non-root `appuser:10001` runner container.
* **Orchestration**: Created `docker-compose.yml` orchestrating FastAPI and PostgreSQL 16 with health checks and volume mounts.

### Sprint 11: Enterprise Health & Prometheus Observability (2026-08-16 – 2026-08-25)
* **Health Subsystem**: Implemented modular health checking subsystem (`PostgresHealthChecker`, `Neo4jHealthChecker`, `GeminiHealthChecker`, `HealthService`, `/health`, `/health/live`, `/health/ready`).
* **Distributed Tracing**: Implemented `RequestLoggingMiddleware` with `X-Request-ID` UUID4 generation, async `ContextVar` propagation, Loguru binding, and response header injection.
* **HTTP Prometheus Metrics**: Registered and observed `http_requests_total` and `http_request_duration_seconds` with parameterized route labeling.
* **LLM Prometheus Telemetry**: Implemented `llm_requests_total`, `llm_request_duration_seconds`, and `llm_tokens_total` metrics partitioned by provider, model, and token type.
* **Metrics Exposition**: Exposed default Prometheus metrics endpoint (`GET /metrics`).

### Documentation & Release Finalization (2026-08-25 – 2026-08-26)
* **System Architecture**: Authored comprehensive architecture documentation in [`docs/ARCHITECTURE.md`](ARCHITECTURE.md).
* **Graph Model Alignment**: Corrected documentation to accurately reflect `MENTIONS` as the sole implemented Neo4j relationship type.
* **Database Architecture**: Authored complete dual-database specification in [`docs/DATABASE.md`](DATABASE.md).
