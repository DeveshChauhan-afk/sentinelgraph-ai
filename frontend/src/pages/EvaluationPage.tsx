import React, { useEffect, useState, useCallback } from 'react';
import {
  Shield,
  ShieldCheck,
  Activity,
  Cpu,
  Database,
  Layers,
  FileCheck2,
  RefreshCw,
  Hash,
  Key,
  FileWarning,
  Binary,
  Compass,
} from 'lucide-react';
import { Badge } from '../components/common/Badge';
import { LoadingState } from '../components/common/LoadingState';
import { ErrorState } from '../components/common/ErrorState';
import { EmptyState } from '../components/common/EmptyState';
import { healthApi } from '../api/health';
import { metricsApi, LlmTelemetryMetrics } from '../api/metrics';
import { HealthSummaryResponse } from '../types/health';

// ---------------------------------------------------------------------------
// Static Governance Specifications (Backend Alignment)
// ---------------------------------------------------------------------------

interface GuardrailLayer {
  layerNumber: number;
  title: string;
  badge: string;
  subsystem: string;
  description: string;
  specifications: string[];
}

const GUARDRAIL_LAYERS: GuardrailLayer[] = [
  {
    layerNumber: 1,
    title: 'Layer 1 — Schema Validation',
    badge: 'Guardrail',
    subsystem: 'ReportParser / Pydantic V2',
    description:
      'Rigorous structural and schema enforcement on raw LLM output before analytical consumption.',
    specifications: [
      'Pydantic structural validation enforcing ProfessionalInvestigationReport model contract',
      'Malformed or schema-invalid AI output is immediately rejected fail-closed',
      'Type-safe normalization of findings, recommendations, and evidence mappings',
    ],
  },
  {
    layerNumber: 2,
    title: 'Layer 2 — Evidence Grounding',
    badge: 'Guardrail',
    subsystem: 'CitationVerifier Subsystem',
    description:
      'Deterministic verification ensuring all cited references strictly exist in the graph context.',
    specifications: [
      'Citation verification comparing citations to InvestigationReportContext',
      'Graph-grounded citations mapped to Neo4j entity, complaint, and evidence keys',
      'Citation coverage metric (ratio of valid citations to total extracted references)',
    ],
  },
  {
    layerNumber: 3,
    title: 'Layer 3 — Hallucination Detection',
    badge: 'Guardrail',
    subsystem: 'HallucinationDetector Engine',
    description:
      'Deterministic knowledge pool auditing preventing speculative or ungrounded synthesis.',
    specifications: [
      'Findings audit against algorithmic critical findings and knowledge pools',
      'Entities audit validating recommended targets against graph knowledge base',
      'Recommendations verification ensuring actions map to verified risk triggers',
      'Unsupported content detection flagging UNSUPPORTED_FINDING or POTENTIAL_HALLUCINATION',
    ],
  },
];

interface GoldenScenarioSpec {
  scenarioId: string;
  name: string;
  targetType: string;
  targetValue: string;
  expectedRiskLevel: 'HIGH' | 'CRITICAL' | 'LOW' | 'INFORMATIONAL';
  expectedFindings: string;
  expectedCitations: string[];
  description: string;
  auditPurpose: string;
}

const GOLDEN_SCENARIOS: GoldenScenarioSpec[] = [
  {
    scenarioId: 'SIMPLE_FRAUD_CASE',
    name: 'Simple Fraud Case',
    targetType: 'phone',
    targetValue: '+919876543210',
    expectedRiskLevel: 'HIGH',
    expectedFindings: '1 critical finding (Phone Number Reuse)',
    expectedCitations: ['C-101', 'C-102', 'EVD-001', '+919876543210'],
    description: 'Standard 2-complaint phone reuse fraud scenario with verified entity linkage.',
    auditPurpose: 'Verifies deterministic dual-complaint correlation and phone entity citation matching.',
  },
  {
    scenarioId: 'ENTITY_REUSE_CASE',
    name: 'Entity Reuse Case',
    targetType: 'upi',
    targetValue: 'scammer@upi',
    expectedRiskLevel: 'CRITICAL',
    expectedFindings: '1 critical finding (High Volume UPI Reuse)',
    expectedCitations: ['C-101', 'C-102', 'C-103', 'C-104', 'C-105', 'EVD-002', 'EVD-003', 'scammer@upi'],
    description: 'High volume UPI ID reuse across 5 complaints with active freeze recommendation.',
    auditPurpose: 'Tests multi-complaint aggregation and urgent financial credential freeze triggers.',
  },
  {
    scenarioId: 'LARGE_FRAUD_RING',
    name: 'Large Fraud Ring',
    targetType: 'fraud_ring',
    targetValue: 'RING-999',
    expectedRiskLevel: 'CRITICAL',
    expectedFindings: '1 critical finding (Coordinated Fraud Syndicate)',
    expectedCitations: ['RING-999', 'C-101', 'C-102', 'C-103', 'EVD-010'],
    description: 'Complex 15-entity organized fraud syndicate spanning 12 connected complaints.',
    auditPurpose: 'Audits network expansion detection and law enforcement referral generation.',
  },
  {
    scenarioId: 'DISCONNECTED_ENTITY_CASE',
    name: 'Disconnected Entity Case',
    targetType: 'entity',
    targetValue: 'DISCONNECTED-001',
    expectedRiskLevel: 'LOW',
    expectedFindings: '0 critical findings (Isolated graph node)',
    expectedCitations: ['DISCONNECTED-001'],
    description: 'Target with zero connected fraud links or isolated graph topology.',
    auditPurpose: 'Negative control benchmark validating zero hallucinated edges and low risk scoring.',
  },
  {
    scenarioId: 'MINIMAL_COMPLAINT_CASE',
    name: 'Minimal Complaint Case',
    targetType: 'complaint',
    targetValue: 'C-MINIMAL-01',
    expectedRiskLevel: 'INFORMATIONAL',
    expectedFindings: '0 critical findings (Sparse baseline)',
    expectedCitations: ['C-MINIMAL-01'],
    description: 'Single complaint scenario with sparse contextual evidence.',
    auditPurpose: 'Tests strict data limitations disclosure and prevents ungrounded algorithmic extrapolation.',
  },
];

interface EvaluationDimensionSpec {
  key: string;
  name: string;
  weight: string;
  formula: string;
  description: string;
}

const EVALUATION_DIMENSIONS: EvaluationDimensionSpec[] = [
  {
    key: 'citation_coverage',
    name: 'Citation Coverage',
    weight: '15%',
    formula: 'findings_with_cites / max(1, report_findings)',
    description: 'Measures the proportion of key findings backed by validated contextual citations.',
  },
  {
    key: 'evidence_utilization',
    name: 'Evidence Utilization',
    weight: '15%',
    formula: 'supporting_evidence_count / max(1, context_evidence)',
    description: 'Measures how comprehensively graph evidence units are synthesized into the dossier.',
  },
  {
    key: 'finding_coverage',
    name: 'Finding Coverage',
    weight: '25%',
    formula: 'report_findings / max(1, context_findings)',
    description: 'Verifies that critical algorithmic findings are fully retained in final AI report.',
  },
  {
    key: 'recommendation_coverage',
    name: 'Recommendation Coverage',
    weight: '20%',
    formula: 'report_recs / max(1, context_recs)',
    description: 'Ensures actionable mitigation steps map directly to verified risk triggers.',
  },
  {
    key: 'timeline_coverage',
    name: 'Timeline Coverage',
    weight: '15%',
    formula: 'report_milestones / max(1, context_milestones)',
    description: 'Evaluates chronological completeness and coverage of temporal incident milestones.',
  },
  {
    key: 'data quality / limitations mentions',
    name: 'Data Quality & Limitations Mentions',
    weight: '10%',
    formula: 'data_quality_mentioned && limitation_mentioned',
    description: 'Mandatory explicit disclosure of data gaps, completeness rating, and analytical boundaries.',
  },
];

interface AuditMechanismSpec {
  name: string;
  key: string;
  mechanism: string;
  subsystem: string;
  description: string;
}

const AUDIT_MECHANISMS: AuditMechanismSpec[] = [
  {
    name: 'Prompt Fingerprinting',
    key: 'prompt_hash',
    mechanism: 'SHA-256 Deterministic Digest',
    subsystem: 'PromptBuilder / PromptMetadata',
    description:
      'A deterministic cryptographic hash computed across the exact system prompt and structured JSON context payload. Bound into every report for immutable audit verification and model provenance.',
  },
  {
    name: 'Distributed Tracing',
    key: 'correlation_id',
    mechanism: 'X-Request-ID Propagation',
    subsystem: 'RequestLoggingMiddleware',
    description:
      'Unique trace identifier injected at the HTTP boundary and threaded through LLM client requests, Neo4j queries, cache keys, and evaluation records for unified cross-service correlation.',
  },
  {
    name: 'Strict Citation Syntax',
    key: 'deterministic citation format',
    mechanism: 'Bracketed Token Matching',
    subsystem: 'CitationVerifier',
    description:
      'Enforced structured syntax [Complaint: <id>], [Evidence: <id>], and [Entity: <value>] parsed via regular expressions and cross-referenced with the source investigation citation map.',
  },
  {
    name: 'Quality Boundary Disclosure',
    key: 'data limitations disclosure',
    mechanism: 'Mandatory Limitations Contract',
    subsystem: 'InvestigationLimitations Schema',
    description:
      'Compulsory report section assessing data completeness score, identifying missing fields, and declaring analytical boundaries to prevent unverified extrapolation.',
  },
];

// ---------------------------------------------------------------------------
// Main Evaluation Page Component
// ---------------------------------------------------------------------------

export const EvaluationPage: React.FC = () => {
  // Live Health State
  const [healthData, setHealthData] = useState<HealthSummaryResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);
  const [healthError, setHealthError] = useState<string | null>(null);

  // Live Telemetry State
  const [telemetryData, setTelemetryData] = useState<LlmTelemetryMetrics | null>(null);
  const [telemetryLoading, setTelemetryLoading] = useState<boolean>(true);
  const [telemetryError, setTelemetryError] = useState<string | null>(null);

  // Refresh State
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<Date>(new Date());

  // Fetch Health from GET /api/v1/health
  const fetchHealth = useCallback(async () => {
    setHealthLoading(true);
    setHealthError(null);
    try {
      const data = await healthApi.getHealth();
      setHealthData(data);
    } catch (err: any) {
      setHealthError(err.message || 'Failed to retrieve system health from /api/v1/health');
      setHealthData(null);
    } finally {
      setHealthLoading(false);
    }
  }, []);

  // Fetch Telemetry from GET /metrics
  const fetchTelemetry = useCallback(async () => {
    setTelemetryLoading(true);
    setTelemetryError(null);
    try {
      const data = await metricsApi.getLlmTelemetry();
      setTelemetryData(data);
    } catch (err: any) {
      setTelemetryError(err.message || 'Failed to scrape Prometheus metrics from /metrics');
      setTelemetryData(null);
    } finally {
      setTelemetryLoading(false);
    }
  }, []);

  // Unified Refresh Handler
  const handleRefreshAll = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await Promise.allSettled([fetchHealth(), fetchTelemetry()]);
      setLastRefreshedAt(new Date());
    } finally {
      setIsRefreshing(false);
    }
  }, [fetchHealth, fetchTelemetry]);

  // Initial Load
  useEffect(() => {
    handleRefreshAll();
  }, [handleRefreshAll]);

  // Status Badge Helper
  const getStatusBadge = (status?: string) => {
    const norm = (status || '').toUpperCase();
    if (norm === 'HEALTHY') return <Badge variant="success">HEALTHY</Badge>;
    if (norm === 'DEGRADED') return <Badge variant="warning">DEGRADED</Badge>;
    if (norm === 'UNHEALTHY') return <Badge variant="danger">UNHEALTHY</Badge>;
    return <Badge variant="neutral">{status || 'UNKNOWN'}</Badge>;
  };

  return (
    <div className="space-y-8 pb-12">
      {/* =================================================================== */}
      {/* 1. Page Header & Governance Banner                                  */}
      {/* =================================================================== */}
      <div className="p-5 rounded-lg bg-sentinel-surface border border-sentinel-border flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <Shield className="w-5 h-5 text-sentinel-accent" />
            <h1 className="text-lg font-bold text-sentinel-text tracking-wide">
              AI Governance & Guardrails
            </h1>
            <Badge variant="info" size="sm">
              Deterministic Verification
            </Badge>
          </div>
          <p className="text-xs text-sentinel-muted max-w-3xl leading-relaxed">
            SentinelGraph enforces deterministic verification, structural schema validation, and
            graph-grounded auditability around AI-generated investigations. AI outputs are treated as
            untrusted until verified against the knowledge graph.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <div className="text-right hidden sm:block">
            <div className="text-[10px] font-mono text-sentinel-dim">Last Polled</div>
            <div className="text-xs font-mono text-sentinel-muted">
              {lastRefreshedAt.toLocaleTimeString()}
            </div>
          </div>
          <button
            onClick={handleRefreshAll}
            disabled={isRefreshing || healthLoading || telemetryLoading}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded bg-sentinel-bg hover:bg-sentinel-surfaceHover border border-sentinel-border text-xs font-medium text-sentinel-text transition-colors disabled:opacity-50"
            title="Re-query live health and Prometheus telemetry"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-sentinel-accent ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>{isRefreshing ? 'Refreshing...' : 'Refresh Telemetry'}</span>
          </button>
        </div>
      </div>

      {/* =================================================================== */}
      {/* 2. Guardrail Pipeline Section                                       */}
      {/* =================================================================== */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-blue-400" />
            <h2 className="text-sm font-semibold text-sentinel-text uppercase tracking-wider">
              Guardrail Pipeline
            </h2>
          </div>
          <span className="text-[11px] font-mono text-sentinel-dim">
            3 Architectural Verification Layers
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {GUARDRAIL_LAYERS.map((layer) => (
            <div
              key={layer.layerNumber}
              className="rounded-lg bg-sentinel-surface border border-sentinel-border p-4 flex flex-col justify-between hover:border-sentinel-borderLight transition-colors"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-mono text-sentinel-dim font-medium">
                    Layer {layer.layerNumber}
                  </span>
                  <Badge variant="info" size="sm">
                    {layer.badge}
                  </Badge>
                </div>
                <h3 className="text-sm font-semibold text-sentinel-text mb-1">
                  {layer.title}
                </h3>
                <div className="text-[11px] font-mono text-sentinel-accent mb-2">
                  {layer.subsystem}
                </div>
                <p className="text-xs text-sentinel-muted mb-3 leading-relaxed">
                  {layer.description}
                </p>
              </div>

              <div className="pt-3 border-t border-sentinel-border/60">
                <div className="text-[10px] font-mono uppercase tracking-wider text-sentinel-dim mb-2 font-medium">
                  Enforcement Rules
                </div>
                <ul className="space-y-1.5">
                  {layer.specifications.map((spec, idx) => (
                    <li key={idx} className="text-xs text-sentinel-muted flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-sentinel-accent shrink-0 mt-1.5" />
                      <span>{spec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* =================================================================== */}
      {/* 3. Live System Health & LLM Telemetry (2 Columns)                   */}
      {/* =================================================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Live System Health */}
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald-400" />
              <h2 className="text-sm font-semibold text-sentinel-text uppercase tracking-wider">
                Live System Health
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="neutral" size="sm">
                Live Telemetry
              </Badge>
              <span className="text-[11px] font-mono text-sentinel-dim">
                GET /api/v1/health
              </span>
            </div>
          </div>

          <div className="rounded-lg bg-sentinel-surface border border-sentinel-border p-4 min-h-[290px] flex flex-col justify-between">
            {healthLoading && !healthData ? (
              <LoadingState
                message="Querying /api/v1/health..."
                description="Validating connectivity to Postgres, Neo4j, and Gemini..."
                className="py-10 border-0 bg-transparent"
              />
            ) : healthError ? (
              <ErrorState
                title="System Health Unavailable"
                message={healthError}
                onRetry={fetchHealth}
                className="py-6 border-0 bg-transparent"
              />
            ) : !healthData ? (
              <EmptyState
                title="No Health Data Available"
                message="The health check endpoint did not return any dependency data."
                className="py-6 border-0 bg-transparent"
              />
            ) : (
              <div className="space-y-4">
                {/* Status Summary Header */}
                <div className="flex items-center justify-between p-2.5 rounded bg-sentinel-bg border border-sentinel-border">
                  <div className="flex items-center gap-3">
                    <div>
                      <div className="text-[10px] font-mono uppercase tracking-wider text-sentinel-dim">
                        Overall Operational Status
                      </div>
                      <div className="text-xs font-semibold text-sentinel-text flex items-center gap-2 mt-0.5">
                        <span>{healthData.service}</span>
                        <span className="text-sentinel-dim font-mono text-[11px]">
                          v{healthData.version}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-mono text-sentinel-muted capitalize">
                      {healthData.environment}
                    </span>
                    {getStatusBadge(healthData.status)}
                  </div>
                </div>

                {/* Dependencies List */}
                <div className="space-y-2">
                  <div className="text-[10px] font-mono uppercase tracking-wider text-sentinel-dim font-medium">
                    Dependency Latency & Status
                  </div>
                  <div className="space-y-1.5">
                    {healthData.dependencies &&
                      Object.entries(healthData.dependencies).map(([depKey, dep]) => {
                        if (!dep) return null;
                        const isHealthy = (dep.status || '').toUpperCase() === 'HEALTHY';
                        const isDegraded = (dep.status || '').toUpperCase() === 'DEGRADED';
                        return (
                          <div
                            key={depKey}
                            className="flex items-center justify-between p-2.5 rounded bg-sentinel-bg/80 border border-sentinel-border/80 hover:border-sentinel-border transition-colors text-xs"
                          >
                            <div className="flex items-center gap-2.5">
                              <Database className="w-3.5 h-3.5 text-sentinel-dim shrink-0" />
                              <div>
                                <span className="font-mono font-medium text-sentinel-text uppercase">
                                  {dep.name || depKey}
                                </span>
                                {dep.critical !== undefined && (
                                  <span className="ml-2 text-[10px] font-mono text-sentinel-dim">
                                    {dep.critical ? '(Critical)' : '(Optional)'}
                                  </span>
                                )}
                                {dep.message && (
                                  <div className="text-[11px] text-sentinel-risk-red mt-0.5">
                                    {dep.message}
                                  </div>
                                )}
                              </div>
                            </div>

                            <div className="flex items-center gap-3">
                              <span className="font-mono text-[11px] text-sentinel-muted">
                                {typeof dep.latency_ms === 'number'
                                  ? `${dep.latency_ms.toFixed(2)} ms`
                                  : 'N/A'}
                              </span>
                              <span
                                className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded border ${
                                  isHealthy
                                    ? 'bg-emerald-950/60 text-emerald-400 border-emerald-800/60'
                                    : isDegraded
                                    ? 'bg-amber-950/60 text-amber-400 border-amber-800/60'
                                    : 'bg-rose-950/60 text-rose-400 border-rose-800/60'
                                }`}
                              >
                                {dep.status.toUpperCase()}
                              </span>
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </div>

                {healthData.timestamp && (
                  <div className="text-[10px] font-mono text-sentinel-dim pt-1">
                    Timestamp: {new Date(healthData.timestamp).toISOString()}
                  </div>
                )}
              </div>
            )}
          </div>
        </section>

        {/* Right Column: LLM Telemetry */}
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-indigo-400" />
              <h2 className="text-sm font-semibold text-sentinel-text uppercase tracking-wider">
                LLM Telemetry
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="neutral" size="sm">
                Live Telemetry
              </Badge>
              <span className="text-[11px] font-mono text-sentinel-dim">
                GET /metrics
              </span>
            </div>
          </div>

          <div className="rounded-lg bg-sentinel-surface border border-sentinel-border p-4 min-h-[290px] flex flex-col justify-between">
            {telemetryLoading && !telemetryData ? (
              <LoadingState
                message="Scraping Prometheus /metrics..."
                description="Parsing llm_requests_total, latency histograms, and token counters..."
                className="py-10 border-0 bg-transparent"
              />
            ) : telemetryError ? (
              <ErrorState
                title="Prometheus Telemetry Scrape Failed"
                message={telemetryError}
                onRetry={fetchTelemetry}
                className="py-6 border-0 bg-transparent"
              />
            ) : !telemetryData ? (
              <EmptyState
                title="No Telemetry Available"
                message="Prometheus metrics could not be parsed."
                className="py-6 border-0 bg-transparent"
              />
            ) : (
              <div className="space-y-4">
                {/* Live Prometheus Scrape Banner */}
                <div className="flex items-center justify-between p-2.5 rounded bg-sentinel-bg border border-sentinel-border">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="text-xs font-semibold text-sentinel-text">
                      Prometheus Registry Active
                    </span>
                  </div>
                  <span className="text-[11px] font-mono text-sentinel-dim">
                    {telemetryData.hasRecordedRequests
                      ? 'Live Traffic Recorded'
                      : 'Zero Requests (Standby)'}
                  </span>
                </div>

                {/* Parsed Metric Cards Grid */}
                <div className="grid grid-cols-2 gap-2.5">
                  <div className="p-3 rounded bg-sentinel-bg/80 border border-sentinel-border/80">
                    <div className="text-[10px] font-mono uppercase tracking-wider text-sentinel-dim mb-1">
                      LLM Requests
                    </div>
                    <div className="text-lg font-mono font-bold text-sentinel-text">
                      {telemetryData.totalRequests.toLocaleString()}
                    </div>
                    <div className="text-[10px] font-mono text-sentinel-muted mt-0.5">
                      llm_requests_total
                    </div>
                  </div>

                  <div className="p-3 rounded bg-sentinel-bg/80 border border-sentinel-border/80">
                    <div className="text-[10px] font-mono uppercase tracking-wider text-sentinel-dim mb-1">
                      Avg Duration
                    </div>
                    <div className="text-lg font-mono font-bold text-sentinel-text">
                      {telemetryData.averageDurationMs !== null
                        ? `${telemetryData.averageDurationMs.toFixed(1)} ms`
                        : 'N/A'}
                    </div>
                    <div className="text-[10px] font-mono text-sentinel-muted mt-0.5">
                      llm_request_duration_seconds
                    </div>
                  </div>

                  <div className="p-3 rounded bg-sentinel-bg/80 border border-sentinel-border/80">
                    <div className="text-[10px] font-mono uppercase tracking-wider text-sentinel-dim mb-1">
                      Prompt Tokens
                    </div>
                    <div className="text-lg font-mono font-bold text-sentinel-text">
                      {telemetryData.promptTokens.toLocaleString()}
                    </div>
                    <div className="text-[10px] font-mono text-sentinel-muted mt-0.5">
                      type="prompt"
                    </div>
                  </div>

                  <div className="p-3 rounded bg-sentinel-bg/80 border border-sentinel-border/80">
                    <div className="text-[10px] font-mono uppercase tracking-wider text-sentinel-dim mb-1">
                      Completion Tokens
                    </div>
                    <div className="text-lg font-mono font-bold text-sentinel-text">
                      {telemetryData.completionTokens.toLocaleString()}
                    </div>
                    <div className="text-[10px] font-mono text-sentinel-muted mt-0.5">
                      type="completion"
                    </div>
                  </div>
                </div>

                {/* Observed Model Label or Empty Graceful Note */}
                {!telemetryData.hasRecordedRequests ? (
                  <div className="p-2.5 rounded bg-sentinel-bg/50 border border-dashed border-sentinel-border text-center text-xs text-sentinel-muted">
                    No LLM inferences have been executed in this process lifetime. Counters will populate
                    automatically when an investigation report is generated.
                  </div>
                ) : (
                  <div className="flex items-center justify-between text-xs text-sentinel-muted pt-1">
                    <span className="font-mono text-[11px] text-sentinel-dim">Observed Models:</span>
                    <span className="font-mono text-[11px] text-sentinel-text font-medium">
                      {telemetryData.models.length > 0
                        ? telemetryData.models.join(', ')
                        : 'Default (gemini-2.5-flash)'}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        </section>
      </div>

      {/* =================================================================== */}
      {/* 4. Golden Evaluation Scenarios Section                              */}
      {/* =================================================================== */}
      <section className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
          <div className="flex items-center gap-2">
            <FileCheck2 className="w-4 h-4 text-amber-400" />
            <h2 className="text-sm font-semibold text-sentinel-text uppercase tracking-wider">
              Golden Evaluation Scenarios
            </h2>
          </div>
          <span className="text-[11px] font-mono text-sentinel-dim">
            Fixed Specifications from golden_dataset.py (Offline Benchmarks)
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {GOLDEN_SCENARIOS.map((scenario) => {
            const riskVariant =
              scenario.expectedRiskLevel === 'CRITICAL'
                ? 'danger'
                : scenario.expectedRiskLevel === 'HIGH'
                ? 'warning'
                : 'neutral';

            return (
              <div
                key={scenario.scenarioId}
                className="rounded-lg bg-sentinel-surface border border-sentinel-border p-4 flex flex-col justify-between hover:border-sentinel-borderLight transition-colors"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <Badge variant="neutral" size="sm">
                      Benchmark Scenario
                    </Badge>
                    <Badge variant={riskVariant} size="sm">
                      Expected: {scenario.expectedRiskLevel}
                    </Badge>
                  </div>

                  <div className="font-mono text-xs font-semibold text-sentinel-text mb-1">
                    {scenario.scenarioId}
                  </div>
                  <div className="text-xs font-medium text-sentinel-accent mb-2">
                    {scenario.name}
                  </div>
                  <p className="text-xs text-sentinel-muted mb-3 leading-relaxed">
                    {scenario.description}
                  </p>
                </div>

                <div className="space-y-2.5 pt-3 border-t border-sentinel-border/60 text-xs">
                  <div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-sentinel-dim block">
                      Target Entity Specification:
                    </span>
                    <div className="font-mono text-sentinel-text mt-0.5 text-[11px] break-all">
                      {scenario.targetValue} ({scenario.targetType})
                    </div>
                  </div>

                  <div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-sentinel-dim block">
                      Expected Findings:
                    </span>
                    <span className="text-sentinel-muted text-[11px]">
                      {scenario.expectedFindings}
                    </span>
                  </div>

                  <div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-sentinel-dim block">
                      Expected Citations:
                    </span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {scenario.expectedCitations.map((cite) => (
                        <span
                          key={cite}
                          className="px-1.5 py-0.5 rounded bg-sentinel-bg border border-sentinel-border font-mono text-[10px] text-sentinel-muted"
                        >
                          {cite}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="pt-2 border-t border-sentinel-border/40 text-[11px] text-sentinel-dim italic">
                    Purpose: {scenario.auditPurpose}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* =================================================================== */}
      {/* 5. Evaluation Dimensions Section                                    */}
      {/* =================================================================== */}
      <section className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
          <div className="flex items-center gap-2">
            <Compass className="w-4 h-4 text-emerald-400" />
            <h2 className="text-sm font-semibold text-sentinel-text uppercase tracking-wider">
              Evaluation Dimensions
            </h2>
          </div>
          <span className="text-[11px] font-mono text-sentinel-dim">
            Engine Definitions from ReportQualityEvaluator (Not Live Scores)
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {EVALUATION_DIMENSIONS.map((dim) => (
            <div
              key={dim.key}
              className="rounded-lg bg-sentinel-surface border border-sentinel-border p-4 flex flex-col justify-between hover:border-sentinel-borderLight transition-colors"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <Badge variant="neutral" size="sm">
                    Evaluation Dimension
                  </Badge>
                  <span className="text-xs font-mono font-semibold text-sentinel-accent">
                    Weight: {dim.weight}
                  </span>
                </div>
                <div className="font-mono text-xs font-semibold text-sentinel-text mb-1">
                  {dim.key}
                </div>
                <div className="text-xs font-medium text-sentinel-muted mb-2">
                  {dim.name}
                </div>
                <p className="text-xs text-sentinel-muted mb-3 leading-relaxed">
                  {dim.description}
                </p>
              </div>

              <div className="pt-2.5 border-t border-sentinel-border/60">
                <span className="text-[10px] font-mono uppercase tracking-wider text-sentinel-dim block mb-1">
                  Calculation Formula:
                </span>
                <code className="text-[11px] font-mono text-sentinel-dim block bg-sentinel-bg px-2 py-1 rounded border border-sentinel-border overflow-x-auto">
                  {dim.formula}
                </code>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* =================================================================== */}
      {/* 6. Auditability & Traceability Section                              */}
      {/* =================================================================== */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
            <h2 className="text-sm font-semibold text-sentinel-text uppercase tracking-wider">
              Auditability & Traceability Mechanisms
            </h2>
          </div>
          <span className="text-[11px] font-mono text-sentinel-dim">
            SOC 2 / ISO 42001 Compliance Controls
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {AUDIT_MECHANISMS.map((mechanism) => {
            const renderIcon = () => {
              if (mechanism.key === 'prompt_hash') return <Hash className="w-3.5 h-3.5 text-cyan-400" />;
              if (mechanism.key === 'correlation_id') return <Key className="w-3.5 h-3.5 text-cyan-400" />;
              if (mechanism.key === 'deterministic citation format')
                return <Binary className="w-3.5 h-3.5 text-cyan-400" />;
              return <FileWarning className="w-3.5 h-3.5 text-cyan-400" />;
            };

            return (
              <div
                key={mechanism.key}
                className="rounded-lg bg-sentinel-surface border border-sentinel-border p-4 flex flex-col justify-between hover:border-sentinel-borderLight transition-colors"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-cyan-400 bg-cyan-950/40 border border-cyan-800/40 px-1.5 py-0.5 rounded flex items-center gap-1.5">
                      {renderIcon()}
                      <span>Audit Mechanism</span>
                    </span>
                  </div>
                  <div className="font-mono text-xs font-semibold text-sentinel-text mb-0.5">
                    {mechanism.key}
                  </div>
                  <div className="text-xs font-medium text-sentinel-accent mb-2">
                    {mechanism.name}
                  </div>
                <p className="text-xs text-sentinel-muted mb-3 leading-relaxed">
                  {mechanism.description}
                </p>
              </div>

              <div className="pt-2.5 border-t border-sentinel-border/60 text-xs">
                <div className="text-[10px] font-mono uppercase tracking-wider text-sentinel-dim">
                  Subsystem:
                </div>
                <div className="font-mono text-sentinel-dim text-[11px] mt-0.5">
                  {mechanism.subsystem}
                </div>
              </div>
            </div>
            );
          })}
        </div>
      </section>
    </div>
  );
};
