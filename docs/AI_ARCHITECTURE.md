# SentinelGraph AI: AI Pipeline Architecture & Reliability Specification

## Executive Summary

**SentinelGraph AI** is an AI-powered Fraud Intelligence Graph platform engineered following Clean Architecture, Repository-Service pattern, and strict **Explainable AI (XAI)** principles. 

The core architectural directive of SentinelGraph AI is:
> **The Backend owns 100% of the investigation reasoning. The LLM owns 0% of the investigation reasoning.**

The Large Language Model (Google Gemini or alternative LLM providers) operates strictly as a constrained, technical report writer. It organizes, formats, and translates deterministic backend context into professional investigation reports without performing independent graph traversals, risk estimation, or evidence inference.

---

## Complete Pipeline Architecture

```
Complaint Records
       │
       ▼
Neo4j Knowledge Graph ──► Timeline Service
                               │
                               ▼
                       Entity Analysis Service
                               │
                               ▼
                       Timeline Analysis Service
                               │
                               ▼
                       Fraud Evolution Service
                               │
                               ▼
                       Evidence Engine (Confidence & Provenance)
                               │
                               ▼
                       InvestigationSummaryService (Canonical DTO)
                               │
                               ▼
                       ReportContextBuilder (Token-Optimized View)
                               │
                               ▼
                       PromptTemplateRegistry & PromptBuilder
                               │
                               ▼
                       PromptRequest (SHA-256 Fingerprinted)
                               │
                               ▼
                       LLMClient (Gemini Provider Interface)
                               │
                               ▼
                       LLMResponse (Normalized Output & Usage)
                               │
                               ▼
                       ReportParser (Schema Validation & Citation Preserving)
                               │
                               ▼
                       ProfessionalInvestigationReport + Telemetry
```

---

## Key Architectural Directives

### 1. Why Reasoning is 100% Deterministic Before AI
In fraud intelligence and law enforcement applications, unconstrained LLM reasoning poses severe risks:
- **Hallucinated relationships**: Inventing non-existent payment connections or co-complaint links.
- **Inconsistent risk scores**: Generating non-reproducible risk assessments for identical evidence.
- **Unverifiable recommendations**: Suggesting legal action without explicit evidentiary triggers.

To eliminate these risks, SentinelGraph AI completes all risk scoring, fraud evolution tracking, graph algorithms, and evidence synthesis inside deterministic Python services (*Timeline, Entity Analysis, Fraud Evolution, Evidence Engine*) prior to engaging the LLM.

### 2. Why the LLM Never Queries Neo4j Directly
The LLM has zero direct database connections. It receives a pre-digested, immutable, token-optimized `InvestigationReportContext`. This ensures:
- **Zero Graph-RAG Injection**: Prompt injections cannot alter Cypher queries or access unauthorized graph nodes.
- **Deterministic Bounds**: The context provided to the LLM represents the absolute boundary of available evidence.
- **High Performance**: Eliminates iterative DB round-trips during LLM generation.

### 3. How Provenance & Citations Are Preserved
Every critical finding and recommendation emitted by `InvestigationSummaryService` carries explicit provenance citations (`related_complaint_ids`, `evidence_ids`, `related_entity_ids`).
`ReportContextBuilder` compiles a structured `citation_map`. The prompt instructions require the LLM to format findings using natural bracketed citations (e.g., `[Complaint: C-101]`, `[Evidence: EVD-001]`).

### 4. How Prompt Versioning & SHA-256 Fingerprinting Work
`PromptMetadata` maintains four independent version layers:
- `prompt_version`: Version of the prompt schema structure (`1.0`).
- `template_version`: Version of the prompt template (`1.0`).
- `report_context_version`: Version of the report view model (`1.0`).
- `summary_version`: Version of the canonical investigation summary (`1.0`).

`PromptBuilder` computes a stable SHA-256 fingerprint digest (`prompt_hash`) over the rendered prompt payload. Identical investigation context and template inputs produce 100% byte-identical prompt hashes.

### 5. How Response Parsing & Validation Work
`ReportParser` processes raw LLM responses through a deterministic multi-step pipeline:
1. **Fence Removal**: Strips Markdown code block wrappers (` ```json ... ``` `).
2. **JSON Extraction**: Extracts valid JSON object bounds.
3. **Schema Validation**: Validates the payload against the Pydantic `ProfessionalInvestigationReport` schema.
4. **Telemetry Attachment**: Injects request correlation ID, latency, token usage, and prompt hash.
5. **Error Translation**: Converts JSON errors or missing schema fields into domain exceptions (`ReportParsingError`, `InvalidReportSchemaError`).

---

## Evaluation & Observability Framework

SentinelGraph AI includes an automated evaluation and observability suite (`app/evaluation`):

| Subsystem | Responsibility | Determinism |
| :--- | :--- | :--- |
| **Golden Scenario Dataset** | Fixed reproducible investigation scenarios for regression testing. | 100% Deterministic |
| **CitationVerifier** | Audits every citation in generated reports against ground truth evidence. | 100% Deterministic |
| **HallucinationDetector** | Audits findings, entities, and recommendations for ungrounded claims. | 100% Deterministic |
| **ReportQualityEvaluator** | Computes citation coverage, evidence utilization, and limitation disclosures. | 100% Deterministic |
| **PerformanceBenchmarker** | Measures latency across summary, context, prompt, LLM, and parser stages. | 100% Deterministic |
| **AIEvaluationReport** | Compiles master evaluation scorecards summarizing status, scores, and audits. | 100% Deterministic |

---

## Summary of Guarantees

1. **Zero Hallucinations**: Any ungrounded claim is caught by `HallucinationDetector`.
2. **Auditability**: Every generated report carries a SHA-256 `prompt_hash` and execution `telemetry`.
3. **Provider Independence**: `LLMClient` interface allows seamless switching between Gemini, OpenAI, Claude, or local LLMs.
4. **Explainability**: Every finding traces directly to underlying complaint records and graph nodes.
