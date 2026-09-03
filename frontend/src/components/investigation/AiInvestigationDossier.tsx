import React from 'react';
import { ProfessionalInvestigationReport } from '../../types';
import { Badge } from '../common/Badge';
import { ErrorState } from '../common/ErrorState';
import { formatDate, getPriorityBadgeVariant, getRiskLevelBadgeVariant } from '../../lib/utils';
import {
  Sparkles,
  Bot,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  FileText,
  Tag,
  ArrowRight,
  GitFork,
  Cpu,
  Bookmark,
  Layers,
  Clock,
  Loader2,
} from 'lucide-react';

interface AiInvestigationDossierProps {
  report: ProfessionalInvestigationReport | null;
  loading: boolean;
  error: string | null;
  onGenerate: () => void;
  onRetry: () => void;
  onSelectEntity?: (entityValue: string) => void;
  targetValue: string;
  hasTarget: boolean;
}

export const AiInvestigationDossier: React.FC<AiInvestigationDossierProps> = ({
  report,
  loading,
  error,
  onGenerate,
  onRetry,
  onSelectEntity,
  targetValue,
  hasTarget,
}) => {
  // Compute overall average confidence from findings if available
  const avgConfidence =
    report && report.key_findings.length > 0
      ? Math.round(
          (report.key_findings.reduce((acc, f) => acc + (f.confidence || 0.8), 0) /
            report.key_findings.length) *
            100
        )
      : null;

  // Helper to parse citations and extract clickable entity values
  const parseCitation = (citation: string) => {
    const entityMatch = citation.match(/\[Entity:\s*([^\]]+)\]/i);
    const complaintMatch = citation.match(/\[Complaint:\s*([^\]]+)\]/i);
    const evidenceMatch = citation.match(/\[Evidence:\s*([^\]]+)\]/i);

    if (entityMatch && entityMatch[1]) {
      const rawEntity = entityMatch[1].trim();
      return {
        type: 'entity',
        label: rawEntity,
        isClickable: true,
        icon: Tag,
      };
    }

    if (complaintMatch && complaintMatch[1]) {
      const rawComplaint = complaintMatch[1].trim();
      return {
        type: 'complaint',
        label: `CASE-${rawComplaint.slice(0, 8).toUpperCase()}`,
        isClickable: true,
        entityValue: `complaint:${rawComplaint}`,
        icon: FileText,
      };
    }

    if (evidenceMatch && evidenceMatch[1]) {
      return {
        type: 'evidence',
        label: `EVD-${evidenceMatch[1].trim().slice(0, 8).toUpperCase()}`,
        isClickable: false,
        icon: Bookmark,
      };
    }

    return {
      type: 'raw',
      label: citation.replace(/[\[\]]/g, ''),
      isClickable: false,
      icon: Bookmark,
    };
  };

  return (
    <div className="space-y-4">
      {/* 1. Prominent Action Bar */}
      <div className="p-4 rounded-lg bg-sentinel-surface border border-sentinel-border flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-blue-950/60 border border-blue-800/80 flex items-center justify-center shrink-0 text-blue-400">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold font-mono text-sentinel-text tracking-wide uppercase">
                AI Graph-RAG Investigation
              </h3>
              <span className="hidden sm:inline-block text-[10px] font-mono px-1.5 py-0.2 rounded bg-sentinel-bg border border-sentinel-border text-sentinel-dim">
                Gemini 3.5 Flash Lite
              </span>
            </div>
            <p className="text-xs text-sentinel-muted mt-0.5">
              Synthesize multi-hop network evidence, evaluate entity reuse, and generate structured findings with deterministic citations.
            </p>
          </div>
        </div>

        <button
          onClick={onGenerate}
          disabled={!hasTarget || loading}
          className={`inline-flex items-center justify-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-lg transition-all shadow-sm shrink-0 ${
            !hasTarget || loading
              ? 'bg-slate-800 text-slate-500 border border-slate-700/50 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-500 text-white border border-blue-400/40 cursor-pointer hover:shadow-blue-900/20 hover:shadow-lg'
          }`}
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-blue-300" />
              <span>Synthesizing Dossier...</span>
            </>
          ) : (
            <>
              <Bot className="w-4 h-4 text-blue-200" />
              <span>Generate AI Investigation</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </>
          )}
        </button>
      </div>

      {/* 2. Loading State */}
      {loading && (
        <div className="p-8 rounded-lg bg-sentinel-surface border border-blue-900/40 flex flex-col items-center justify-center text-center space-y-4">
          <div className="relative">
            <div className="w-14 h-14 rounded-full bg-blue-950/60 border border-blue-800 flex items-center justify-center text-blue-400 animate-pulse">
              <Sparkles className="w-7 h-7" />
            </div>
            <Loader2 className="w-14 h-14 text-blue-500 animate-spin absolute inset-0 opacity-70" />
          </div>

          <div>
            <div className="text-sm font-semibold font-mono text-sentinel-text">
              Synthesizing Graph-RAG Investigation Dossier
            </div>
            <div className="text-xs text-sentinel-muted max-w-md mx-auto mt-1">
              Executing multi-hop retrieval over Neo4j fraud graph, correlating shared mule accounts, and generating evidence-backed findings for target <span className="font-mono text-blue-400">{targetValue}</span>.
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 w-full max-w-xl text-[11px] font-mono pt-2">
            <div className="p-2 rounded bg-sentinel-bg border border-sentinel-border text-sentinel-muted flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span className="truncate">1. Evidence Context Built</span>
            </div>
            <div className="p-2 rounded bg-sentinel-bg border border-blue-800/60 text-blue-400 flex items-center gap-2 animate-pulse">
              <Cpu className="w-3.5 h-3.5 text-blue-400 shrink-0" />
              <span className="truncate">2. Gemini 3.5 Reasoning...</span>
            </div>
            <div className="p-2 rounded bg-sentinel-bg border border-sentinel-border text-sentinel-dim flex items-center gap-2">
              <Layers className="w-3.5 h-3.5 text-sentinel-dim shrink-0" />
              <span className="truncate">3. Verifying Citations</span>
            </div>
          </div>
        </div>
      )}

      {/* 3. Error State */}
      {error && !loading && (
        <ErrorState
          title="AI Investigation Generation Failed"
          message={error}
          onRetry={onRetry}
        />
      )}

      {/* 4. Complete AI Investigation Dossier */}
      {report && !loading && (
        <div className="rounded-lg bg-sentinel-surface border border-sentinel-border overflow-hidden space-y-6 p-5">
          {/* Dossier Header & Badges */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-sentinel-border">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-mono uppercase text-sentinel-dim">
                  Report ID: {report.report_id}
                </span>
                <span className="text-sentinel-dim text-xs">•</span>
                <span className="text-xs text-sentinel-dim font-mono">
                  {formatDate(report.generated_at)}
                </span>
              </div>
              <h3 className="text-base font-bold text-sentinel-text font-mono flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-blue-400" />
                <span>AI Investigation Dossier:</span>
                <span className="text-blue-400">{report.target_value}</span>
              </h3>
            </div>

            {/* Badges: Risk Level + Confidence + Scope */}
            <div className="flex flex-wrap items-center gap-2">
              <Badge
                variant={getRiskLevelBadgeVariant(
                  report.executive_summary?.overall_risk_level
                )}
                size="md"
              >
                {report.executive_summary?.overall_risk_level || 'HIGH'} RISK
              </Badge>

              {avgConfidence !== null && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-blue-950/60 border border-blue-800/60 text-blue-400 text-xs font-mono font-semibold">
                  <Bot className="w-3 h-3 text-blue-400" />
                  <span>{avgConfidence}% Confidence</span>
                </span>
              )}

              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-sentinel-bg border border-sentinel-border text-sentinel-muted text-xs font-mono">
                <Layers className="w-3 h-3 text-sentinel-dim" />
                <span>
                  {report.investigation_scope?.total_complaints || 0} cases
                </span>
              </span>
            </div>
          </div>

          {/* Section A: Executive Summary */}
          {report.executive_summary && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-sentinel-dim font-semibold">
                <FileText className="w-3.5 h-3.5 text-blue-400" />
                <span>Executive Summary</span>
              </div>

              <div className="p-4 rounded-lg bg-sentinel-bg/80 border border-sentinel-border text-sm leading-relaxed text-sentinel-text font-sans">
                {report.executive_summary.summary_text}
              </div>

              {/* Key Takeaways */}
              {report.executive_summary.key_takeaways &&
                report.executive_summary.key_takeaways.length > 0 && (
                  <div className="p-3.5 rounded-lg bg-sentinel-bg/40 border border-sentinel-border">
                    <span className="text-[11px] font-mono uppercase text-sentinel-dim block mb-2 font-medium">
                      Key Takeaways:
                    </span>
                    <ul className="space-y-1.5 text-xs text-sentinel-muted">
                      {report.executive_summary.key_takeaways.map((takeaway, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5 shrink-0" />
                          <span>{takeaway}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
            </div>
          )}

          {/* Section B: Key Findings with Deterministic Citations */}
          {report.key_findings && report.key_findings.length > 0 && (
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-sentinel-dim font-semibold">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                  <span>Key Findings ({report.key_findings.length})</span>
                </div>
                <span className="text-[10px] font-mono text-sentinel-dim">
                  Citations mapped from Neo4j evidence
                </span>
              </div>

              <div className="space-y-2.5">
                {report.key_findings.map((finding) => (
                  <div
                    key={finding.finding_id}
                    className="p-3.5 rounded-lg bg-sentinel-bg/60 border border-sentinel-border hover:border-sentinel-borderLight transition-all"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-sentinel-surface border border-sentinel-border text-sentinel-dim">
                          {finding.finding_id}
                        </span>
                        <h4 className="text-xs font-bold text-sentinel-text font-mono">
                          {finding.title}
                        </h4>
                      </div>

                      <div className="flex items-center gap-1.5 shrink-0">
                        <Badge
                          variant={getRiskLevelBadgeVariant(finding.severity)}
                        >
                          {finding.severity}
                        </Badge>
                        <span className="text-[10px] font-mono text-sentinel-dim">
                          {Math.round((finding.confidence || 0.8) * 100)}% conf
                        </span>
                      </div>
                    </div>

                    <p className="text-xs text-sentinel-muted leading-relaxed mb-2.5">
                      {finding.description}
                    </p>

                    {/* Citations row */}
                    {finding.citations && finding.citations.length > 0 && (
                      <div className="pt-2 border-t border-sentinel-border/50 flex flex-wrap items-center gap-1.5">
                        <span className="text-[10px] font-mono text-sentinel-dim mr-1">
                          Evidence:
                        </span>
                        {finding.citations.map((rawCitation, cIdx) => {
                          const parsed = parseCitation(rawCitation);
                          const Icon = parsed.icon;

                          if (parsed.isClickable && onSelectEntity) {
                            return (
                              <button
                                key={cIdx}
                                onClick={() =>
                                  onSelectEntity(parsed.entityValue || parsed.label)
                                }
                                title={`Pivot to ${parsed.label}`}
                                className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-sentinel-surface hover:bg-sentinel-surfaceHover border border-blue-900/60 text-blue-400 text-[10px] font-mono transition-colors group cursor-pointer"
                              >
                                <Icon className="w-2.5 h-2.5" />
                                <span>{parsed.label}</span>
                                <ArrowRight className="w-2 h-2 opacity-50 group-hover:opacity-100" />
                              </button>
                            );
                          }

                          return (
                            <span
                              key={cIdx}
                              className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-sentinel-surface border border-sentinel-border text-sentinel-dim text-[10px] font-mono"
                            >
                              <Icon className="w-2.5 h-2.5" />
                              <span>{parsed.label}</span>
                            </span>
                          );
                        })}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Section C: Recommended Actions (Distinct Visual Styling) */}
          {report.recommendations && report.recommendations.length > 0 && (
            <div className="space-y-3 pt-2">
              <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-sentinel-dim font-semibold">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>Recommended Analyst Actions ({report.recommendations.length})</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {report.recommendations.map((rec) => (
                  <div
                    key={rec.recommendation_id}
                    className="p-3.5 rounded-lg border border-emerald-900/40 bg-emerald-950/10 flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <span className="text-[10px] font-mono text-emerald-400 font-semibold">
                          {rec.recommendation_id}
                        </span>
                        <Badge variant={getPriorityBadgeVariant(rec.priority)}>
                          {rec.priority} PRIORITY
                        </Badge>
                      </div>

                      <div className="text-xs font-bold text-sentinel-text mb-1">
                        {rec.action}
                      </div>

                      <p className="text-xs text-sentinel-muted leading-relaxed mb-2">
                        {rec.rationale}
                      </p>
                    </div>

                    {/* Target entities / trigger chips */}
                    <div className="pt-2 border-t border-emerald-900/30 flex flex-wrap items-center justify-between gap-2">
                      <span className="text-[10px] font-mono text-sentinel-dim">
                        Trigger: {rec.trigger}
                      </span>

                      {rec.target_entities && rec.target_entities.length > 0 && (
                        <div className="flex flex-wrap items-center gap-1">
                          {rec.target_entities.map((entity, eIdx) => (
                            <button
                              key={eIdx}
                              onClick={() => onSelectEntity?.(entity)}
                              className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-sentinel-surface hover:bg-sentinel-surfaceHover border border-sentinel-border text-emerald-300 transition-colors"
                              title="Pivot to target"
                            >
                              {entity}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Section D: Fraud Network Evolution / Timeline */}
          {report.fraud_network_evolution && (
            <div className="p-3.5 rounded-lg bg-sentinel-bg/40 border border-sentinel-border space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-xs font-mono uppercase tracking-wider text-sentinel-dim font-semibold">
                  <GitFork className="w-3.5 h-3.5 text-purple-400" />
                  <span>Network Evolution</span>
                </div>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-purple-950/40 border border-purple-800/40 text-purple-300">
                  {report.fraud_network_evolution.network_stage}
                </span>
              </div>
              <p className="text-xs text-sentinel-muted leading-relaxed">
                {report.fraud_network_evolution.evolution_narrative}
              </p>
            </div>
          )}

          {/* Section E: Telemetry & Audit Footer */}
          {report.telemetry && (
            <div className="pt-3 border-t border-sentinel-border/50 flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-sentinel-dim">
              <div className="flex items-center gap-2">
                <Cpu className="w-3 h-3 text-blue-400" />
                <span>Model: {report.telemetry.model || 'Gemini 3.5'}</span>
                <span>•</span>
                <Clock className="w-3 h-3 text-amber-400" />
                <span>Latency: {report.telemetry.latency_ms?.toFixed(1)}ms</span>
              </div>

              <div className="truncate max-w-xs">
                Corr: {report.telemetry.correlation_id}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
