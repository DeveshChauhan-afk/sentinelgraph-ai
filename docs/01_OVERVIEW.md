# 🛡️ SentinelGraph AI: System Overview & Problem Domain

## 1. Executive Summary

**SentinelGraph AI** is an enterprise-grade, full-stack cyber fraud intelligence and risk management platform engineered for digital public safety. The platform tackles one of the fastest-growing threats to the digital economy: organized cyber fraud syndicates that weaponize digital arrest coercion, UPI payment redirection, phishing portals, and mule banking networks.

Traditional cybercrime record-management systems treat every citizen or bank complaint as an isolated ticket. As a result, critical connections—such as a single mobile number coordinating fifty digital arrest scams across four states, or a single UPI VPA siphoning victim funds across dozens of phishing cases—remain hidden inside unstructured case notes.

SentinelGraph AI transforms disconnected fraud complaints into an interconnected **Fraud Intelligence Knowledge Graph**. By combining:
1. A **PostgreSQL 16** relational transactional system of record;
2. A **Neo4j AuraDB / Community** property graph modeling entity-complaint networks;
3. A **100% deterministic Python Explainable AI (XAI)** analysis and evidence scoring engine;
4. A strictly bounded **Google Gemini** generative AI model for entity extraction and formal report writing;
5. An interactive **React 18 & Cytoscape.js** analyst console;
6. An enterprise **Prometheus & Grafana** observability stack;

SentinelGraph AI enables law enforcement agencies, cyber cells, and financial fraud units to uncover syndicate infrastructure in milliseconds, trace fraud network evolution over time, and generate legally defensible, evidence-grounded investigation dossiers.

---

## 2. Problem Domain & Threat Landscape

Digital financial fraud has evolved from isolated opportunistic scams into industrialized cybercrime syndicates. In India and globally, several scam categories inflict devastating financial and psychological harm:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               MODERN FRAUD SYNDICATE PATTERNS                          │
├─────────────────────────┬──────────────────────────┬───────────────────────────────────┤
│ Scheme Category         │ Modus Operandi           │ Syndicate Infrastructure Reused   │
├─────────────────────────┼──────────────────────────┼───────────────────────────────────┤
│ Digital Arrest Scams    │ Impersonating police /   │ Shared VOIP phone numbers, spoofed│
│                         │ CBI / customs via video  │ Skype/WhatsApp accounts, forged   │
│                         │ call; coercing victims   │ legal notices, mule bank accounts │
│                         │ into isolation & funds   │ for "security verification"       │
│                         │ transfers                │                                   │
├─────────────────────────┼──────────────────────────┼───────────────────────────────────┤
│ UPI / QR Payment Scams  │ Deceptive refund links,  │ Shared UPI VPAs (Virtual Payment  │
│                         │ fake merchant collect    │ Addresses), recurring SIM cards,  │
│                         │ requests, spoofed static │ fraudulent merchant handles       │
│                         │ QR codes                 │                                   │
├─────────────────────────┼──────────────────────────┼───────────────────────────────────┤
│ Phishing & Impersonation│ Cloned banking portals,  │ Disposable domain names, phishing │
│                         │ credential harvesting,   │ URLs, brand-impersonation emails, │
│                         │ fake customer-support APK│ automated SMS gateway channels    │
│                         │ files                    │                                   │
├─────────────────────────┼──────────────────────────┼───────────────────────────────────┤
│ Mule Banking Syndicates │ Layered fund dispersion  │ Layered savings/current accounts, │
│                         │ across multi-tier mule   │ mule networks, coordinated cash   │
│                         │ bank accounts            │ withdrawal locations              │
└─────────────────────────┴──────────────────────────┴───────────────────────────────────┘
```

### Critical Gaps in Existing Investigation Tools
1. **Siloed Relational Data**: Relational databases excel at storing tabular records, but detecting multi-hop loops and shared identifiers across hundreds of thousands of records requires expensive recursive joins that cannot scale for real-time triage.
2. **Unstructured Evidence**: Over 80% of critical fraud indicators (phone numbers, VPAs, mule accounts, URLs) are buried in free-text complaint descriptions submitted by citizens.
3. **The "Black Box" LLM Risk**: Using unconstrained generative AI to reason about crimes leads to dangerous hallucinations: invented connections, ungrounded accusations, and non-reproducible risk scores that cannot withstand judicial scrutiny.
4. **Investigation Latency**: Human analysts manually correlating complaints spend hours cross-referencing spreadsheets and departmental databases while syndicate accounts remain active and continue laundering victim funds.

---

## 3. The SentinelGraph AI Solution

SentinelGraph AI solves these challenges by enforcing a strict architectural separation of responsibilities between **transactional durability**, **graph topology**, **deterministic algorithmic reasoning**, and **constrained generative AI synthesis**.

```
Citizen / Bank / Cyber Cell Complaint
                 │
                 ▼
 ┌───────────────────────────────┐
 │   FastAPI Backend (Async)     │
 └──────┬─────────────────┬──────┘
        │ (1) Durable     │ (2) Asynchronous
        │     Intake      │     Background Task
        ▼                 ▼
 ┌─────────────┐   ┌───────────────────────────────┐
 │ PostgreSQL  │   │  Google Gemini 2.5 Flash SDK  │
 │ (System of  │   │  (Constrained Extraction)     │
 │  Record)    │   └──────────────┬────────────────┘
 └─────────────┘                  │ Extracted Entities
                                  ▼
                   ┌───────────────────────────────┐
                   │ Neo4j Property Graph          │
                   │ (:Complaint)-[:MENTIONS]->    │
                   │ (:Entity)                     │
                   └──────────────┬────────────────┘
                                  │ Topological Evidence
                                  ▼
                   ┌───────────────────────────────┐
                   │ Deterministic Python Engines  │
                   │ • Timeline Reconstruction     │
                   │ • Fraud Evolution Modeling    │
                   │ • Evidence Scoring (0.0 - 1.0)│
                   │ • Risk Metric Calculation     │
                   └──────────────┬────────────────┘
                                  │ Canonical Case File DTO
                                  ▼
                   ┌───────────────────────────────┐
                   │ Google Gemini Report Writer   │
                   │ • Zero Autonomous Reasoning   │
                   │ • SHA-256 Prompt Hashing      │
                   │ • Citation-Preserving Dossier │
                   └──────────────┬────────────────┘
                                  │
                                  ▼
                   ┌───────────────────────────────┐
                   │ React 18 Analyst Workspace    │
                   │ • Cytoscape.js Network Graph  │
                   │ • Chronological Timeline      │
                   │ • Governance & Telemetry UI   │
                   └───────────────────────────────┘
```

---

## 4. Architectural Truths & Design Invariants

To maintain absolute technical integrity, SentinelGraph AI operates under explicit architectural invariants:

1. **PostgreSQL 16 is the Transactional System of Record**:
   Raw complaint text, legal case references, triage states, reporter metadata, timestamps, and audit records are durably committed to PostgreSQL before any downstream processing occurs.
2. **Neo4j Persists a Strict Bipartite/Star Topology**:
   Neo4j persists **only** one relationship type: `(:Complaint)-[:MENTIONS]->(:Entity)`. High-level conceptual relationships (`REPORTED_IN`, `TRANSFERRED_TO`, `ASSOCIATED_WITH`, `CO_OCCURS_WITH`) are **never** persisted in the database; they are dynamically computed via graph traversals.
3. **Zero Autonomous LLM Reasoning**:
   All investigation logic, multi-hop traversals, risk scoring, timeline reconstruction, and evidence severity classifications are executed by **100% deterministic Python code**. Google Gemini is never permitted to calculate risk scores, determine guilt, or speculate beyond provided evidence.
4. **Strict Isolation of LLM Provider**:
   Google Gemini **never** directly accesses, queries, or modifies PostgreSQL or Neo4j. The model interacts exclusively through structured Pydantic DTOs passed by backend services.
5. **Decoupled Ingestion Resilience**:
   Failure or rate-limiting of external AI services or Neo4j never rolls back or compromises the primary PostgreSQL complaint record. Ingestion errors are isolated and logged.
6. **Immutable Audit Trails**:
   Every generated AI investigation dossier is stamped with an immutable execution correlation ID, an execution latency metric, token counters, and a **SHA-256 prompt hash** (`prompt_hash`) ensuring that any generated report can be reproduced and verified.

---

## 5. System Components Summary

| Component | Technology | Primary Function |
| :--- | :--- | :--- |
| **Analyst Web Console** | React 18, TypeScript, Vite, Tailwind CSS | Single-pane operational workspace providing risk overview, interactive Cytoscape.js network exploration, investigation dossiers, and governance telemetry. |
| **Ingress & Static Host** | Nginx Alpine (Reverse Proxy) | Serves compiled SPA assets on port 80; reverse-proxies `/api/`, `/health`, and `/metrics` to the backend; enforces compression and security headers. |
| **Application Core** | FastAPI, Python 3.13, Uvicorn | Asynchronous REST API orchestrating ingestion, graph queries, deterministic analysis, and external LLM communication. |
| **Relational Store** | PostgreSQL 16 (asyncpg / SQLAlchemy) | Transactional system of record storing complaints, metadata, legal case references, and audit logs. |
| **Graph Intelligence** | Neo4j 5.26 Community / AuraDB | Labeled property graph storing entities, complaints, and `MENTIONS` edges with startup DDL uniqueness constraints. |
| **AI Extraction & Reports** | Google Gemini (google-genai SDK) | Structured entity extraction from complaints and formal prose generation for investigation dossiers. |
| **Deterministic XAI** | Pure Python Algorithms | Timeline reconstruction, entity lifecycle analysis, fraud evolution modeling, evidence confidence scoring, and risk metrics. |
| **Observability Engine** | Prometheus 2.53 & Grafana 11.1 | 15s metric scraping, 5 production alert rules, pre-provisioned Grafana operational dashboards, and health probes. |

---

## 6. Documentation Map

The SentinelGraph AI technical documentation is structured into dedicated, deep-dive manuals:

* [`docs/01_OVERVIEW.md`](01_OVERVIEW.md): System overview, problem domain, and foundational design principles *(Current Document)*.
* [`docs/02_ARCHITECTURE.md`](02_ARCHITECTURE.md): Full-stack request lifecycle, component interactions, and data boundaries.
* [`docs/03_DATABASE.md`](03_DATABASE.md): Dual-database architecture, PostgreSQL schema, Alembic migrations, and Neo4j graph model.
* [`docs/04_API_REFERENCE.md`](04_API_REFERENCE.md): Comprehensive REST API reference, mounted routes, request/response models, and error codes.
* [`docs/05_AI_PIPELINE.md`](05_AI_PIPELINE.md): Deterministic investigation architecture, Graph-RAG pipeline, prompt hashing, and Gemini boundaries.
* [`docs/06_EVALUATION_GOVERNANCE.md`](06_EVALUATION_GOVERNANCE.md): 3-layer guardrail verification, 5 golden scenarios, quality evaluator, and benchmarking.
* [`docs/07_FRONTEND.md`](07_FRONTEND.md): React 18 analyst console, Cytoscape.js network visualization, hash routing, and Nginx proxy.
* [`docs/08_OBSERVABILITY.md`](08_OBSERVABILITY.md): Prometheus metrics catalog, scrape configuration, alert rules, Grafana dashboards, and health checks.
* [`docs/09_DEPLOYMENT_OPERATIONS.md`](09_DEPLOYMENT_OPERATIONS.md): Docker Compose orchestration, environment configuration, database migrations, and operational runbooks.
* [`docs/10_SECURITY.md`](10_SECURITY.md): Security posture, unauthenticated reality disclosure, Pydantic validation, SecretStr protection, and hardening.
* [`docs/11_CHANGELOG.md`](11_CHANGELOG.md): Historical record of engineering sprints and platform releases through Sprint 12.
* [`docs/12_ROADMAP.md`](12_ROADMAP.md): Strategic product roadmap distinguishing Implemented v1, Near-Term Hardening, and Future V2+ capabilities.
