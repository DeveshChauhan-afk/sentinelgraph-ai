# 🗺️ SentinelGraph AI: Product & Engineering Roadmap

## 1. Roadmap Architecture & Tiering Strategy

To maintain complete architectural honesty, the SentinelGraph AI product and engineering roadmap is strictly partitioned into three distinct horizons:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   SENTINELGRAPH AI PRODUCT HORIZONS                    │
├──────────────────────────┬─────────────────────────────────────────────┤
│ Horizon 1: Implemented   │ Fully completed, verified, and active in the │
│ Full-Stack Platform (v1) │ repository codebase today.                  │
├──────────────────────────┼─────────────────────────────────────────────┤
│ Horizon 2: Near-Term     │ Immediate engineering hardening required for│
│ Production Hardening     │ enterprise enterprise rollout (e.g. Auth).  │
├──────────────────────────┼─────────────────────────────────────────────┤
│ Horizon 3: Genuine V2+   │ Substantive new capabilities (e.g. Voice,   │
│ Future Capabilities      │ Multimodal OCR, Regional Indian Languages). │
└──────────────────────────┴─────────────────────────────────────────────┘
```

> [!IMPORTANT]
> **Anti-Drift Invariant**:
> Capabilities that are **already implemented** (such as the React 18 web console, Cytoscape.js network visualization, Prometheus metrics, Grafana dashboards, health endpoints, or Docker containerization) are strictly categorized under **Horizon 1**. They must **never** be relegated back to future roadmap sections.

---

## 2. Horizon 1: Implemented Full-Stack Platform (Current Status)

The following capabilities are 100% implemented, covered by 287 automated unit and regression tests, and verified in the repository:

### 2.1 Backend Core & Dual-Database Persistence
* [x] **PostgreSQL 16 System of Record**: Async SQLAlchemy 2.0 (`asyncpg`) storage for raw complaint narratives, reporter classifications, operational priorities, and audit timestamps.
* [x] **Two Versioned Alembic Migrations**:
  * `3d3cf359c2a1`: Base table creation, 5 custom ENUM types, and check constraints.
  * `e7c2a19d4b8f`: Unique constraint `uq_incidents_case_reference` on external case IDs.
* [x] **Neo4j 5.26 Property Graph**: Async driver integration modeling extracted fraud entities across 9 node labels (`Complaint`, `Phone`, `UPI`, `Email`, `URL`, `BankAccount`, `Organization`, `Person`, `Location`).
* [x] **Startup DDL Uniqueness Constraints**: 9 programmatic database-enforced uniqueness constraints (`uq_<label>_id` on `n.id IS UNIQUE`) executed automatically on application startup.
* [x] **Bipartite MENTIONS Topology**: Complete graph intelligence operating strictly over `(:Complaint)-[:MENTIONS]->(:Entity)` edges with zero ungrounded conceptual relationships.
* [x] **Atomic Idempotent Persistence**: Cypher `MERGE` statements guaranteeing duplicate-free ingestion under concurrent loads.

### 2.2 Deterministic Explainable AI (XAI) Engine
* [x] **Zero Autonomous LLM Reasoning**: 100% of analytical investigation reasoning, multi-hop traversals, risk scoring, timeline reconstruction, and evidence severity ratings executed in deterministic Python.
* [x] **Timeline Reconstruction Engine**: Chronological ordering of connected complaints, dormant interval detection, and temporal velocity metrics.
* [x] **Entity Evolution Modeling**: Lifecycle tracking, first-seen/last-seen timestamps, and cross-complaint reuse counts.
* [x] **Fraud Evolution Classifier**: Deterministic detection of payment and communication infrastructure expansion stages (`EMERGING`, `EXPANDING`, `MATURE_SYNDICATE`).
* [x] **Evidence Engine**: Rule-based severity assignment and mathematical confidence scoring ($0.0 \le c \le 1.0$).
* [x] **Canonical Case File Assembly**: Immutable `InvestigationSummary` DTOs compiling verified ground truth.

### 2.3 Constrained Generative AI (Google Gemini)
* [x] **Structured Entity Extraction**: Google Gemini extracting standardized identifiers from unstructured citizen narratives.
* [x] **Executive Dossier Formatting**: Gemini translating verified case files into formal prose dossiers with citation preservation.
* [x] **Prompt Fingerprinting**: SHA-256 cryptographic digest (`prompt_hash`) stamped on all prompts and reports for auditability.
* [x] **Reliability Hardening**: Non-blocking `asyncio.to_thread` execution, per-attempt timeout guard (`asyncio.wait_for`), non-retryable timeouts, and bounded exponential backoff retries for transient HTTP 429/5xx status codes.
* [x] **Strict Isolation**: Gemini has zero direct database credentials or query execution capabilities.

### 2.4 React 18 Analyst Web Console
* [x] **Modern Single Page Application**: React 18, TypeScript, Vite, Tailwind CSS, and Lucide React.
* [x] **Hash-Based SPA Routing**: `#risk-overview`, `#investigate`, and `#evaluation` views.
* [x] **Risk Overview Dashboard**: Global fraud KPIs, top connected entities, shared infrastructure hubs, and recent complaints.
* [x] **Interactive Cytoscape.js Visualization**: Topological network exploration, 1–5 hop depth controls, physics layouts (`cose`, `concentric`, `breadthfirst`), and node inspection drawer.
* [x] **Chronological Timeline View**: Visual sequence of multi-hop complaint occurrences.
* [x] **Investigation Dossier View**: Structured findings, risk justifications, and actionable recommendations.
* [x] **AI Governance Console**: Transparency dashboard for 3-layer guardrails, 5 golden scenarios, and quality formulas.

### 2.5 Observability, Evaluation & Deployment
* [x] **Prometheus Metrics Engine**: Custom metrics tracking HTTP traffic (`http_requests_total`, `http_request_duration_seconds`) and LLM telemetry (`llm_requests_total`, `llm_request_duration_seconds`, `llm_tokens_total`).
* [x] **Five Production Alert Rules**: `HighHttp5xxErrorRate`, `ElevatedHttpRequestLatency`, `ReadinessProbeFailing`, `HighLlmErrorRate`, `ElevatedLlmRequestLatency`.
* [x] **Pre-Provisioned Grafana Dashboard**: `sentinelgraph-operations.json` visualizing throughput, latency quantiles, token consumption, and dependency health.
* [x] **Modular Health Probes**: `/health/live` (liveness), `/health/ready` (dependency readiness), and `/health` (operational summary).
* [x] **Offline Evaluation Suite**: Five golden scenarios, `CitationVerifier`, `HallucinationDetector`, `ReportQualityEvaluator`, and `PerformanceBenchmarker`.
* [x] **Unified Docker Orchestration**: Root Docker Compose orchestrating all 6 containers with frontend on port 80.
* [x] **Backend CI**: GitHub Actions automated workflow running Ruff, dry-run Alembic migrations, and pytest.

---

## 3. Horizon 2: Near-Term Production Hardening

The following items represent targeted engineering hardening tasks required prior to operational deployment in production law enforcement or banking infrastructure:

| Capability | Category | Description | Priority |
| :--- | :--- | :--- | :--- |
| **Authentication & RBAC** | Security | Replace `/api/v1/auth/` placeholder with OAuth2 / OIDC / JWT Bearer token authentication and role-based permissions (`analyst`, `investigator`, `admin`). | **P0 (Critical)** |
| **Frontend CI Pipeline** | CI / CD | Expand GitHub Actions workflow (`.github/workflows/ci.yml`) to include frontend linting (`npm run lint`), type-checking (`tsc --noEmit`), and Vitest component testing (currently CI covers backend only). | **P1 (High)** |
| **Live Evaluation API Endpoint**| API / Governance| Expose a protected operational endpoint (`POST /api/v1/governance/evaluate`) allowing auditors to execute the quality evaluator dynamically against live reports. | **P2 (Medium)** |
| **Database Pool Autoscaling** | Scalability | Implement dynamic connection pool scaling and read-replica routing for PostgreSQL to handle burst complaint ingestion. | **P2 (Medium)** |
| **Secret Management Integration**| Security | Migrate from environment file secrets to cloud-native key vaults (e.g. AWS Secrets Manager, HashiCorp Vault) with automated secret rotation. | **P2 (Medium)** |

---

## 4. Horizon 3: Genuine V2+ Future Capabilities

These capabilities represent major substantive evolutions of the SentinelGraph AI platform:

### 4.1 Multimodal Voice Scam Audio Analysis
* **Problem**: Digital arrest scams increasingly involve direct audio coercion via spoofed WhatsApp/Skype VoIP calls.
* **Capability**: Direct ingestion and transcription of audio call recordings using OpenAI Whisper or Gemini Audio.
* **Analysis**: Acoustic stress detection, voice cloning matching (detecting identical synthetic voices used across complaints), and automated coercion cue extraction.

### 4.2 Counterfeit Document & Fake Notice OCR
* **Problem**: Scammers intimidate victims by issuing forged arrest warrants, fake CBI summon notices, and cloned police identity cards.
* **Capability**: Multimodal computer vision pipeline analyzing uploaded PDF/image evidence to detect forged official seals, fraudulent letterheads, and inconsistent typographic layouts.

### 4.3 Multilingual & Regional Indian Language Support
* **Problem**: Cyber fraud complaints are frequently drafted in regional Indian languages (Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati).
* **Capability**: Multilingual entity extraction pipelines fine-tuned to recognize localized phrasing, slang, and dialectal fraud descriptions while preserving standardized entity normalization.

### 4.4 Direct Banking Switch Freeze Connectors
* **Problem**: Mitigating victim loss requires freezing mule accounts within minutes of complaint submission.
* **Capability**: Direct, authenticated webhooks connecting SentinelGraph AI recommendations to NPCI, RBI, and partner commercial banking fraud switches to trigger temporary holds on flagged UPI VPAs and bank accounts.

### 4.5 National Cyber Crime Reporting Portal (NCRP) Ingestion Adapter
* **Problem**: Complaints are currently submitted via standalone SentinelGraph AI channels.
* **Capability**: Automated API connectors ingesting real-time complaint feeds from the Indian National Cyber Crime Reporting Portal (cybercrime.gov.in) and state police CCTNS databases.

### 4.6 Distributed Streaming Architecture (Kafka / Debezium)
* **Problem**: Scaling to millions of concurrent national complaints exceeds direct REST-to-PostgreSQL throughput limits.
* **Capability**: Transition from in-process background tasks to an enterprise event-driven architecture using Apache Kafka and Debezium Change Data Capture (CDC) for asynchronous graph construction.
