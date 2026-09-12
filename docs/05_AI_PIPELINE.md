# 🧠 SentinelGraph AI: AI Pipeline, Graph-RAG & LLM Engine

## 1. The Core Philosophy: Deterministic Grounding Over Autonomy

A foundational tenet of SentinelGraph AI is that **generative AI must never act as an autonomous investigator or decision-maker in public safety and legal investigations**.

When unconstrained Large Language Models (LLMs) are tasked with open-ended crime analysis, they exhibit severe vulnerabilities:
1. **Hallucinated Linkages**: Inventing connections between innocent citizens and criminal syndicates based on semantic coincidence.
2. **Non-Reproducible Risk Scoring**: Assigning arbitrary risk ratings (e.g. 85% today, 42% tomorrow) for identical evidence.
3. **Black-Box Reasoning**: Formulating conclusions without an auditable chain of evidence that can withstand court scrutiny.
4. **Prompt Injection Susceptibility**: Malicious reporters injecting instructions inside complaint narratives to bypass detection.

### The SentinelGraph AI Directive
* **100% of Analytical Investigation Reasoning is Deterministic Python Logic**:
  Network traversal, timeline reconstruction, velocity calculation, entity reuse tracking, fraud evolution stage classification, evidence scoring, and risk level assignment are executed by pure, deterministic Python algorithms.
* **0% of Risk Scoring or Link Discovery is Delegated to the LLM**:
  Google Gemini is strictly constrained to two specific non-decisional cognitive tasks:
  1. **Structured Entity Extraction**: Extracting standardized fraud identifiers from messy citizen text narratives.
  2. **Professional Report Synthesis**: Translating a pre-computed, verified canonical case file into polished executive prose with strict citation preservation.
* **Gemini NEVER Directly Queries PostgreSQL or Neo4j**:
  The LLM has zero direct database connectivity, credentials, or query execution privileges. It receives structured Pydantic view models and returns structured JSON.

---

## 2. End-to-End Graph-RAG Workflow

The Graph Retrieval-Augmented Generation (Graph-RAG) pipeline operates across seven sequential phases:

```
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 1: Intake & Durable Relational Commit                            │
│ Citizen submits complaint -> PostgreSQL commits record (ACID)          │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 2: AI Entity Extraction (Google Gemini)                          │
│ Raw narrative -> ExtractedEntities (Phone, UPI, Bank, URL, etc.)       │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 3: Graph Construction & Persistence (Neo4j)                      │
│ GraphBuilder formats nodes/edges -> Cypher MERGE (:Complaint)-[:MENTIONS]│
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 4: Deterministic Graph Evidence Gathering                        │
│ QueryService fetches multi-hop neighbors, related incidents, rings     │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 5: Deterministic Analysis Engines                                │
│ TimelineService + EntityAnalysis + FraudEvolution + EvidenceEngine     │
│ -> Canonical InvestigationSummary DTO ("Case File")                    │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 6: Report Context & Prompt Fingerprinting                        │
│ ReportContextBuilder -> PromptBuilder (SHA-256 prompt_hash)            │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 7: Constrained Generation & Schema Validation                    │
│ GeminiClient (Timeout/Retry) -> ReportParser -> Validated Report       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. The Deterministic Analysis Engines

Before any prompt is constructed for Gemini, five deterministic Python engines process graph evidence:

### 3.1 [`TimelineService`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/services/timeline_service.py)
* Traverses the target entity's multi-hop network in Neo4j to collect all connected complaints.
* Orders events chronologically by complaint timestamp.
* Calculates first-seen and last-seen timestamps, active lifespan, and event cadences.

### 3.2 [`EntityAnalysisService`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/services/entity_analysis_service.py)
* Evaluates entity reuse frequencies across independent complaints.
* Detects identifier hopping (e.g. suspect switching phone numbers while retaining the same UPI VPA).
* Tracks cross-complaint degree centrality.

### 3.3 [`TimelineAnalysisService`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/services/timeline_analysis_service.py)
* Measures velocity metrics (complaints per week/month).
* Identifies dormant intervals and sudden burst activity spikes (e.g. 5 complaints within 48 hours).

### 3.4 [`FraudEvolutionService`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/services/fraud_evolution_service.py)
* Detects syndicate infrastructure expansion stages:
  * `EMERGING`: Single complaint, isolated identifiers.
  * `EXPANDING`: Reused communication channels, multi-tier mule accounts.
  * `MATURE_SYNDICATE`: Dense co-occurrence across phone, UPI, email, and bank nodes.

### 3.5 [`EvidenceEngine`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/services/evidence_engine.py)
* Applies rule-based evidentiary criteria to synthesize verified findings.
* Assigns objective severity ratings: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`.
* Computes mathematical confidence scores ($0.0 \le c \le 1.0$) based on data completeness and multi-complaint corroboration.

### 3.6 [`InvestigationSummaryService`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/services/investigation_summary_service.py)
* Compiles all engine outputs into the canonical `InvestigationSummary` DTO ("Case File DTO").
* This DTO contains the absolute ground truth for the investigation.

---

## 4. Prompt Engineering & SHA-256 Fingerprinting

To format the canonical case file into an executive dossier, the system uses [`PromptBuilder`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/services/prompt_builder.py).

### 4.1 Report Context View Model
The full case file can be large. [`ReportContextBuilder`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/services/report_context_builder.py) compiles a token-optimized view model ([`InvestigationReportContext`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/schemas/investigation_report_context.py)) containing:
* Target identifier metadata;
* Pre-computed risk level and score;
* Verified finding titles, descriptions, and supporting entity/complaint IDs;
* Recommended actions and their deterministic triggers;
* Known graph entities and complaints for citation validation.

### 4.2 SHA-256 Prompt Fingerprinting (`prompt_hash`)
For every prompt generated, `PromptBuilder` calculates a SHA-256 cryptographic digest of the complete serialized instructions and context:

```python
prompt_content = f"{system_prompt}\n{serialized_context}\n{instructions}"
prompt_hash = hashlib.sha256(prompt_content.encode("utf-8")).hexdigest()
```

* The `prompt_hash` is stamped directly on the resulting `ProfessionalInvestigationReport`.
* Enables legal teams and forensic auditors to verify whether an AI report was generated from identical input context or if tampering occurred.

### 4.3 Constrained Generation Contract
The system prompt explicitly commands Gemini:
1. **Zero Extrapolation**: Never invent complaints, phone numbers, UPI VPAs, or amounts not explicitly in the context.
2. **Preserve Risk Invariants**: Output the exact `overall_risk_level` and `overall_risk_score` provided in the context.
3. **Preserve Citations**: Every finding must include valid citation IDs matching the known graph entities and complaints provided in the context.
4. **Strict JSON Schema**: Emit raw JSON matching `ProfessionalInvestigationReport` without preamble or conversational text.

---

## 5. LLM Client Reliability & Hardening

Interactions with Google Gemini are handled by [`GeminiClient`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/ai/client.py) using the modern `google-genai` SDK. Implemented hardening controls include:

### 5.1 Async Event Loop Isolation (`asyncio.to_thread`)
The Google GenAI Python SDK executes network requests synchronously under the hood. To prevent blocking FastAPI's asynchronous event loop, all calls are offloaded to Python's background thread pool:
```python
response = await asyncio.wait_for(
    asyncio.to_thread(
        self._client.models.generate_content,
        model=model_name,
        contents=contents,
        config=config,
    ),
    timeout=timeout_seconds,
)
```

### 5.2 Per-Attempt Timeout Guard
* Enforced via `asyncio.wait_for(timeout=GEMINI_TIMEOUT_SECONDS)`.
* If a call exceeds the timeout (default: 30 seconds), `asyncio.TimeoutError` is raised.
* **Timeout Invariant**: Timeouts are treated as non-retryable. Timed-out attempts immediately raise `LLMTimeoutError` to prevent runaway cascading background calls.

### 5.3 Bounded Exponential Backoff Retry Budget
* Configured via `GEMINI_MAX_RETRIES` (default: 3 total attempts).
* **Retryable Errors**:
  * HTTP 429 (Rate Limit / Quota Exhaustion).
  * HTTP 500, 502, 503, 504 (Provider Server Errors).
  * `google.genai.errors.ServerError`.
  * Transient network socket drops.
* **Non-Retryable Errors**:
  * HTTP 400 (Invalid prompt syntax).
  * HTTP 401, 403 (Invalid API key / unauthorized).
  * HTTP 404 (Model not found).
  * `asyncio.TimeoutError`.
* **Backoff Calculation**:
  ```python
  delay = min(initial_delay * (2 ** (attempt - 1)), max_delay)
  await asyncio.sleep(delay)
  ```

### 5.4 Prometheus Metric Instrumentation
Every single provider invocation is metered:
* `llm_requests_total` partitioned by `provider="gemini"`, `model`, and `status="success"|"error"`.
* `llm_request_duration_seconds` histogram measuring provider latency.
* `llm_tokens_total` counter tracking `prompt` and `completion` token usage extracted from Gemini's `usage_metadata`.

---

## 6. Structured Report Parsing & Citation Preservation

The raw JSON completion emitted by Gemini is validated and parsed by [`ReportParser`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/services/investigation/report_parser.py):

![AI Investigation Output Report](../visuals/investigation.png)
*Structured investigation dossier rendered in the analyst console, featuring evidence-grounded findings, confidence scoring, entity risk breakdowns, and actionable containment steps.*

1. **Markdown Fence Stripping**: Extracts valid JSON content if the model wraps output in ` ```json ... ``` ` blocks.
2. **Pydantic Validation**: Validates the payload against [`ProfessionalInvestigationReport`](file:///c:/Devesh/DeveshChauhan/Devesh%20Chauhan/sentinelgraph-ai/backend/app/schemas/report.py).
3. **Citation Verification**: Ensures that every citation in findings maps to real complaint references or entities from the graph context.
4. **Metadata & Telemetry Injection**: Attaches execution latency, token counts, correlation IDs, and the SHA-256 `prompt_hash` before returning the final report to the caller.
