# SentinelGraph AI: Product & Engineering Roadmap

## 1. Executive Summary & Strategy

SentinelGraph AI has achieved its **Backend v1 completion milestone**: a scalable, asynchronous FastAPI platform engineered for public safety and fraud intelligence. The platform combines a hybrid dual-database architecture (**PostgreSQL** for transactional complaint durability and **Neo4j AuraDB** for topological knowledge graph intelligence), a deterministic Explainable AI (XAI) reasoning pipeline, automated AI evaluation, containerized deployment, and enterprise Prometheus observability.

The SentinelGraph AI engineering and product roadmap is organized into three strategic horizons:

1. **Horizon 1: Completed Backend v1** &mdash; Foundation, graph intelligence engine, deterministic investigation reporting, evaluation harness, and observability telemetry.
2. **Horizon 2: Near-Term Hardening & Operational Readiness** &mdash; Documentation finalization, database constraint hardening, pre-built Grafana observability dashboards, alerting rules, and extended resilience testing.
3. **Horizon 3: Future V2+ Capabilities** &mdash; Multimodal scam intelligence, interactive investigator web UI, multi-language processing, law enforcement/banking webhooks, multi-provider LLM integrations, and advanced graph machine learning.

> **Note**: This roadmap reflects architectural and product direction. To ensure engineering integrity, no speculative delivery dates or fabricated deadlines are assigned to future capabilities.

---

## 2. Completed Milestones: Backend v1

The following capabilities represent completed, tested, and documented functionality within the SentinelGraph AI repository across Sprints 1–11:

### Core Relational & Persistence Engine
* **Asynchronous Web Foundation**: FastAPI backend running with asynchronous request handling and Pydantic-based domain modeling.
* **Relational Storage**: PostgreSQL accessed via SQLAlchemy 2.0 async engine (`asyncpg`) with production connection pooling (`DB_POOL_SIZE=10`, `DB_MAX_OVERFLOW=20`).
* **Schema & Auditing**: Concrete `incidents` table with custom ENUMs, risk-score range check constraints (`0.0 <= risk_score <= 1.0`), and timezone-aware timestamps.
* **Schema Versioning**: Database migration management using Alembic (`3d3cf359c2a1_create_incidents_table.py`) with synchronous `psycopg2` migration execution.
* **Repository Pattern**: Generic `BaseRepository` and domain `IncidentRepository` with explicit service-owned transaction boundaries (`commit`/`rollback`).

### Knowledge Graph & Topological Intelligence
* **Graph Database**: Fully integrated Neo4j AuraDB property graph accessed via `AsyncGraphDatabase`.
* **Standardized Node Model**: 9 implemented node labels (`Complaint`, `Phone`, `UPI`, `Email`, `URL`, `BankAccount`, `Organization`, `Person`, `Location`) with standardized `<prefix>:<value>` identifiers.
* **Relationship Topology**: Strict persistence of the `MENTIONS` relationship (`(:Complaint)-[:MENTIONS]->(:Entity)`).
* **Topological Algorithms**: Variable-length fraud ring detection (`[*0..6]`), network summary analytics, degree centrality and risk scoring (`_calculate_risk`), shortest path traversal (`shortestPath`), and multi-complaint shared entity correlation.
* **Persistence Idempotency**: Atomic Cypher `MERGE` queries guaranteeing idempotent graph ingestion.

### Graph-RAG & Investigation Intelligence
* **Graph-RAG Retrieval**: Graph Retrieval-Augmented Generation (`InvestigationService`) gathering multi-hop topological context and metrics into structured evidence objects.
* **Investigation Caching**: High-performance in-memory TTL caching (`InvestigationCache`, 300s TTL) for repeated investigation requests.
* **Timeline Reconstruction**: Multi-hop chronological complaint timeline assembly (`TimelineService`).
* **Fraud Evolution Modeling**: Tracking infrastructure expansion milestones across payment channels and communication identifiers (`FraudEvolutionService`).
* **Evidence Engine**: Deterministic evidence severity categorization and mathematical confidence evaluation (`EvidenceEngine`).

### Deterministic Explainable AI (XAI) & Evaluation
* **Strict XAI Architecture**: 100% of investigation reasoning, risk scoring, and evidence correlation is executed deterministically in the backend; the LLM owns 0% of investigation reasoning.
* **Constrained Report Generation**: Google Gemini operates as a structured report writer translating verified case files (`InvestigationSummary`, `InvestigationReportContext`) into formal reports.
* **Prompt Reproducibility**: Versioned prompt template registry and SHA-256 prompt fingerprinting (`prompt_hash`) for byte-identical reproducibility.
* **Citation Preservation**: Explicit evidentiary grounding in generated reports (`[Complaint: ...]`, `[Evidence: ...]`).
* **Automated Reliability Suite**: Evaluation subsystem (`app/evaluation`) comprising `GoldenDataset`, `CitationVerifier`, `HallucinationDetector`, `ReportQualityEvaluator`, and `PerformanceBenchmarker`.

### Containerization, CI & Enterprise Observability
* **Multi-Stage Dockerfile**: Isolated build stage and hardened non-root runtime container (`appuser:10001`).
* **Local Composition**: `docker-compose.yml` orchestrating FastAPI and PostgreSQL 16 with health checks and volume persistence.
* **Continuous Integration**: GitHub Actions workflow (`.github/workflows/ci.yml`) automating Ruff linting and pytest test suites.
* **Health Subsystem**: Modular health checking framework (`/health`, `/health/live`, `/health/ready`) validating PostgreSQL, Neo4j, and Gemini connectivity.
* **Distributed Request Tracing**: `RequestLoggingMiddleware` generating `X-Request-ID` UUIDs propagated via async `ContextVar` into structured Loguru logs and response headers.
* **Prometheus Metrics**: HTTP metrics (`http_requests_total`, `http_request_duration_seconds`) and LLM telemetry (`llm_requests_total`, `llm_request_duration_seconds`, `llm_tokens_total`) exposed via `GET /metrics`.

---

## 3. Near-Term Hardening & Operational Readiness

The following items represent logical, high-priority engineering enhancements to harden the existing v1 architecture. These are proposed improvements, not completed features:

| Priority Area | Proposed Engineering Work | Status |
| :--- | :--- | :---: |
| **Documentation Completion** | Author comprehensive endpoint specifications in `docs/API.md` and formal product requirements in `docs/PRD.md`. | Proposed |
| **Neo4j Schema Hardening** | Implement database-level uniqueness constraints (e.g. `CREATE CONSTRAINT FOR (n:Entity) REQUIRE n.id IS UNIQUE`) and explicit indexes on `lookup_value`. *(Current idempotency relies on application-level Cypher `MERGE`)*. | Proposed |
| **Observability Dashboards** | Build pre-configured Grafana dashboard JSON models for HTTP throughput, endpoint latencies (p50/p95/p99), and Gemini token budgets. | Proposed |
| **Alerting Rules** | Define Prometheus Alertmanager rules for sustained `5xx` error rates, LLM quota exhaustion, and dependency health degradation. | Proposed |
| **Cloud Deployment Manifests** | Author cloud deployment configurations (e.g., Cloud Run, AWS ECS) with automated startup migration execution (`alembic upgrade head`). *(Note: `deployment/Dockerfile`, `deployment/railway.json`, and `deployment/vercel.json` are currently placeholder files)*. | Proposed |
| **Extended Resilience Testing** | Expand automated testing to include database reconnection recovery, transient LLM error handling policies, and concurrent ingestion load stress tests. | Proposed |

---

## 4. Future Capabilities: V2+

The following capabilities represent strategic product horizons outlined in project documentation. These are strictly future capabilities and are not part of the Backend v1 implementation:

### Multimodal Scam Intelligence
* **Voice Scam Audio Analysis**: Audio ingestion, speech recognition, and acoustic pattern analysis for digital arrest and impersonation schemes.
* **Counterfeit Document & Screenshot OCR**: Vision-based text and metadata extraction from counterfeit notices, warrants, and payment receipts.
* **QR Code & Phishing Image Verification**: Automated verification and security analysis of fraudulent QR codes and spoofed payment portals.

### Interactive Real-Time Investigator Platform
* **Investigator Web Application**: Interactive visual dashboard for exploring the Neo4j fraud knowledge graph.
* **Real-Time Fraud Alert Streams**: Live alert streaming and notification feeds for active fraud rings and linked complaints.
* **Case File Reporting & Export**: Structured generation and export of comprehensive investigation dossiers.

### Multi-Language & Regional Dialect Processing
* **Regional Language Intake**: Ingestion of complaints submitted in regional Indian languages.
* **Localized Entity Extraction**: Named Entity Recognition (NER) models adapted for regional dialects, transliterations, and local fraud terminology.

### Law Enforcement & Financial Sector Integrations
* **Cyber Crime Portal Integration**: Standardized export formats and integration adapters for cyber crime reporting agencies and state cyber cells.
* **Legal Draft Generation**: Automated compilation of standardized legal complaint drafts and evidentiary summaries from verified graph evidence.
* **Financial Sector Collaboration**: Integration interfaces for financial institutions to receive fraud intelligence and suspect entity alerts.

### Multi-Provider LLM Expansion
* **Pluggable LLM Providers**: Implement additional concrete adapters for the abstract `LLMClient` interface, including OpenAI, Claude, and local LLMs.
* **Dynamic Provider Routing**: Configurable model routing based on latency, cost, and availability requirements.

### Advanced Graph Machine Learning
* **Community Detection Algorithms**: Automated graph community clustering to identify distinct fraud syndicates within complex networks.
* **Topological Graph Embeddings**: Graph embeddings and topological machine learning to discover emerging fraud patterns.

---

## 5. Non-Goals & Architectural Boundaries

To maintain engineering focus and clarity, the following principles govern SentinelGraph AI's scope:

1. **No Speculative Commitments**: Roadmap items are directional capabilities and do not represent contractual delivery dates.
2. **No Claim of Active Railway/Vercel Deployments**: The current deployment baseline is defined by `backend/Dockerfile` and `backend/docker-compose.yml`. Root deployment placeholders are not active targets.
3. **No Distributed 2PC or Outbox/CDC**: The v1 architecture uses an application-orchestrated dual-write pattern with failure isolation. Distributed two-phase commit or Kafka-based event streaming are out of scope for v1.
4. **Single Persisted Graph Relationship**: The property graph schema strictly uses `MENTIONS`. Conceptual relationships (such as association or money transfer) are evaluated dynamically via graph traversal, not stored as separate relationship types.
5. **Clear Separation of Backend v1 from Future Horizons**: Multimodal analysis, multi-language processing, frontend web applications, and direct banking integrations are non-goals for Backend v1 and belong strictly to Future V2+.

---

## 6. Related Documentation

* [`README.md`](../README.md): Project overview, showcase architecture diagram, and feature catalog.
* [`docs/ARCHITECTURE.md`](ARCHITECTURE.md): System architecture specification, middleware pipeline, and observability design.
* [`docs/DATABASE.md`](DATABASE.md): Dual-database architecture, relational schema, and property graph model.
* [`docs/CHANGELOG.md`](CHANGELOG.md): Historical record of development milestones across Sprints 1–11.
* [`docs/AI_ARCHITECTURE.md`](AI_ARCHITECTURE.md): Deterministic Explainable AI (XAI) pipeline and reliability evaluation suite.
