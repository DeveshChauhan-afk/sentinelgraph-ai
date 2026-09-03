import React, { useEffect, useState, useCallback } from 'react';
import { graphApi } from '../../api';
import { EntityRiskResponse } from '../../types';
import { Badge } from '../common/Badge';
import { ErrorState } from '../common/ErrorState';
import { EmptyState } from '../common/EmptyState';
import { getRiskLevelBadgeVariant } from '../../lib/utils';
import {
  ShieldAlert,
  AlertTriangle,
  FileText,
  Share2,
  Tag,
  CheckCircle2,
  RefreshCw,
  Activity,
} from 'lucide-react';

interface RiskIntelligencePanelProps {
  targetValue: string;
  className?: string;
}

export const RiskIntelligencePanel: React.FC<RiskIntelligencePanelProps> = ({
  targetValue,
  className = '',
}) => {
  const [riskData, setRiskData] = useState<EntityRiskResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchRisk = useCallback(async () => {
    if (!targetValue) return;

    setLoading(true);
    setError(null);
    setRiskData(null); // Clear stale risk data from previous target

    try {
      const data = await graphApi.getEntityRisk(targetValue.trim());
      setRiskData(data);
    } catch (err: any) {
      setError(
        err.message ||
          `Unable to compute risk intelligence for target "${targetValue}".`
      );
    } finally {
      setLoading(false);
    }
  }, [targetValue]);

  useEffect(() => {
    fetchRisk();
  }, [fetchRisk]);

  // Color mappings based on risk level
  const getScoreTheme = (level: string) => {
    switch (level?.toUpperCase()) {
      case 'HIGH':
        return {
          textColor: 'text-sentinel-risk-red',
          bgColor: 'bg-sentinel-risk-redBg',
          borderColor: 'border-sentinel-risk-redBorder',
          progressColor: 'bg-sentinel-risk-red',
        };
      case 'MEDIUM':
        return {
          textColor: 'text-sentinel-risk-amber',
          bgColor: 'bg-sentinel-risk-amberBg',
          borderColor: 'border-sentinel-risk-amberBorder',
          progressColor: 'bg-sentinel-risk-amber',
        };
      case 'LOW':
        return {
          textColor: 'text-sentinel-risk-green',
          bgColor: 'bg-sentinel-risk-greenBg',
          borderColor: 'border-sentinel-risk-greenBorder',
          progressColor: 'bg-sentinel-risk-green',
        };
      default:
        return {
          textColor: 'text-sentinel-muted',
          bgColor: 'bg-sentinel-surface',
          borderColor: 'border-sentinel-border',
          progressColor: 'bg-sentinel-muted',
        };
    }
  };

  return (
    <div
      className={`rounded-lg bg-sentinel-surface border border-sentinel-border overflow-hidden ${className}`}
    >
      {/* 1. Panel Header */}
      <div className="p-3.5 border-b border-sentinel-border flex items-center justify-between bg-sentinel-surface select-none">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-sentinel-accent" />
          <h3 className="text-xs font-bold font-mono uppercase text-sentinel-text tracking-wider">
            Risk Intelligence
          </h3>
          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-sentinel-bg border border-sentinel-border text-sentinel-dim truncate max-w-xs">
            TARGET: {targetValue}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className="hidden sm:flex items-center gap-1.5 text-[10px] font-mono text-sentinel-dim">
            <Activity className="w-3 h-3 text-emerald-400" />
            <span>Graph Heuristics</span>
          </div>

          <button
            onClick={fetchRisk}
            disabled={loading}
            title="Recompute Risk Profile"
            className="p-1 rounded bg-sentinel-bg hover:bg-sentinel-surfaceHover border border-sentinel-border text-sentinel-muted hover:text-sentinel-text transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* 2. Main Content Body */}
      <div className="p-4">
        {loading ? (
          <div className="space-y-3">
            <div className="flex items-center gap-4">
              <div className="w-24 h-16 bg-sentinel-surfaceHover rounded animate-pulse" />
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-sentinel-surfaceHover rounded w-1/3 animate-pulse" />
                <div className="h-2.5 bg-sentinel-surfaceHover rounded w-full animate-pulse" />
              </div>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2">
              {[...Array(4)].map((_, i) => (
                <div
                  key={i}
                  className="h-12 bg-sentinel-surfaceHover rounded animate-pulse"
                />
              ))}
            </div>
          </div>
        ) : error ? (
          <ErrorState
            title="Risk Assessment Unavailable"
            message={error}
            onRetry={fetchRisk}
          />
        ) : !riskData ? (
          <EmptyState
            title="No risk intelligence recorded"
            message={`No automated risk score or heuristic signals exist for target "${targetValue}".`}
          />
        ) : (
          (() => {
            const theme = getScoreTheme(riskData.risk_level);

            return (
              <div className="space-y-4">
                {/* Top Section: Prominent Score + Metrics Grid */}
                <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-center">
                  {/* Left Column: Prominent Score Display (5 cols) */}
                  <div className="md:col-span-5 p-3.5 rounded-lg bg-sentinel-bg border border-sentinel-border flex items-center justify-between gap-4">
                    <div>
                      <div className="text-[10px] font-mono uppercase text-sentinel-dim tracking-wider mb-1">
                        Composite Risk Score
                      </div>
                      <div className="flex items-baseline gap-1.5">
                        <span
                          className={`text-3xl font-extrabold font-mono ${theme.textColor}`}
                        >
                          {riskData.risk_score}
                        </span>
                        <span className="text-xs font-mono text-sentinel-dim">
                          / 100
                        </span>
                      </div>

                      {/* Progress Bar */}
                      <div className="w-36 h-1.5 bg-sentinel-surface rounded-full overflow-hidden mt-2 border border-sentinel-border">
                        <div
                          className={`h-full ${theme.progressColor}`}
                          style={{
                            width: `${Math.min(Math.max(riskData.risk_score, 5), 100)}%`,
                          }}
                        />
                      </div>
                    </div>

                    <div className="flex flex-col items-end justify-center">
                      <span className="text-[10px] font-mono text-sentinel-dim uppercase mb-1">
                        Threat Level
                      </span>
                      <Badge
                        variant={getRiskLevelBadgeVariant(riskData.risk_level)}
                        size="md"
                      >
                        {riskData.risk_level} RISK
                      </Badge>
                    </div>
                  </div>

                  {/* Right Column: Supporting Indicator Metric Cards (7 cols) */}
                  <div className="md:col-span-7 grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                    {/* Linked Complaints */}
                    <div className="p-2.5 rounded bg-sentinel-bg border border-sentinel-border">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-mono uppercase text-sentinel-dim">
                          Incidents
                        </span>
                        <FileText className="w-3.5 h-3.5 text-blue-400" />
                      </div>
                      <div className="font-mono text-base font-bold text-sentinel-text">
                        {riskData.metrics.incident_count}
                      </div>
                      <div className="text-[10px] text-sentinel-muted truncate">
                        Linked complaints
                      </div>
                    </div>

                    {/* Neighboring Entities */}
                    <div className="p-2.5 rounded bg-sentinel-bg border border-sentinel-border">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-mono uppercase text-sentinel-dim">
                          Neighbors
                        </span>
                        <Share2 className="w-3.5 h-3.5 text-purple-400" />
                      </div>
                      <div className="font-mono text-base font-bold text-sentinel-text">
                        {riskData.metrics.neighbor_count}
                      </div>
                      <div className="text-[10px] text-sentinel-muted truncate">
                        Connected nodes
                      </div>
                    </div>

                    {/* Entity Classification */}
                    <div className="p-2.5 rounded bg-sentinel-bg border border-sentinel-border col-span-2 sm:col-span-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-mono uppercase text-sentinel-dim">
                          Entity Type
                        </span>
                        <Tag className="w-3.5 h-3.5 text-emerald-400" />
                      </div>
                      <div className="font-mono text-base font-bold text-sentinel-text truncate">
                        {riskData.entity.label || 'Entity'}
                      </div>
                      <div className="text-[10px] text-sentinel-muted truncate">
                        Resolved schema
                      </div>
                    </div>
                  </div>
                </div>

                {/* Bottom Section: "Why this entity is risky" (Evidence & Reasons) */}
                <div className="p-3 rounded-lg bg-sentinel-bg/70 border border-sentinel-border">
                  <div className="flex items-center gap-1.5 mb-2 text-xs font-mono uppercase tracking-wider text-sentinel-text font-semibold">
                    <AlertTriangle className="w-3.5 h-3.5 text-sentinel-risk-amber" />
                    <span>Why this entity is risky</span>
                    <span className="text-[10px] text-sentinel-dim font-normal">
                      (Backend Heuristic Signals)
                    </span>
                  </div>

                  {riskData.reasons && riskData.reasons.length > 0 ? (
                    <ul className="space-y-1.5">
                      {riskData.reasons.map((reason, idx) => (
                        <li
                          key={idx}
                          className="flex items-start gap-2 text-xs text-sentinel-muted"
                        >
                          <span className="w-1.5 h-1.5 rounded-full bg-sentinel-risk-amber mt-1.5 shrink-0" />
                          <span className="font-mono text-sentinel-text">
                            {reason}
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <div className="flex items-center gap-2 text-xs text-sentinel-muted">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      <span>
                        No adverse signals identified. Entity falls within standard baseline behavior.
                      </span>
                    </div>
                  )}
                </div>
              </div>
            );
          })()
        )}
      </div>
    </div>
  );
};
