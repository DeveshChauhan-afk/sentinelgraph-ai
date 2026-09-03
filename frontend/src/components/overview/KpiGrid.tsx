import React from 'react';
import { GraphSummary, TopRiskEntityResponse } from '../../types';
import { Share2, Network, FileText, AlertTriangle, Activity } from 'lucide-react';
import { ErrorState } from '../common/ErrorState';

interface KpiGridProps {
  summary: GraphSummary | null;
  topRisk: TopRiskEntityResponse[] | null;
  loading: boolean;
  error?: string | null;
  onRetry?: () => void;
}

export const KpiGrid: React.FC<KpiGridProps> = ({
  summary,
  topRisk,
  loading,
  error,
  onRetry,
}) => {
  if (error && !loading && !summary) {
    return (
      <ErrorState
        title="Unable to load network metrics"
        message={error}
        onRetry={onRetry}
      />
    );
  }

  // Derive high-risk count from top-risk entities where risk_level === 'HIGH' or risk_score >= 70
  const highRiskCount = topRisk
    ? topRisk.filter(
        (entity) => entity.risk_level === 'HIGH' || entity.risk_score >= 70
      ).length
    : null;

  const cards = [
    {
      id: 'total_entities',
      label: 'Total Entities',
      value: summary ? summary.total_nodes.toLocaleString() : '—',
      description: 'Resolved nodes across graph',
      icon: Share2,
      color: 'text-blue-400',
    },
    {
      id: 'relationships',
      label: 'Graph Relationships',
      value: summary ? summary.total_edges.toLocaleString() : '—',
      description: 'Mentions & co-occurrences',
      icon: Network,
      color: 'text-purple-400',
    },
    {
      id: 'complaints',
      label: 'Reported Complaints',
      value: summary ? summary.complaints.toLocaleString() : '—',
      description: 'Ingested incident records',
      icon: FileText,
      color: 'text-emerald-400',
    },
    {
      id: 'high_risk',
      label: 'High-Risk Entities',
      value: highRiskCount !== null ? highRiskCount.toString() : '—',
      description: 'Score ≥ 70 in top cluster',
      icon: AlertTriangle,
      color: 'text-sentinel-risk-red',
    },
    {
      id: 'avg_connectivity',
      label: 'Avg Connectivity',
      value: summary ? summary.average_degree.toFixed(2) : '—',
      description: 'Edges per entity node',
      icon: Activity,
      color: 'text-amber-400',
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3.5">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <div
            key={card.id}
            className="p-3.5 rounded-lg bg-sentinel-surface border border-sentinel-border hover:border-sentinel-borderLight transition-colors"
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] font-mono uppercase text-sentinel-dim font-medium tracking-wider truncate">
                {card.label}
              </span>
              <Icon className={`w-4 h-4 ${card.color} shrink-0`} />
            </div>

            <div className="flex items-baseline gap-1.5">
              {loading ? (
                <div className="h-7 w-16 bg-sentinel-surfaceHover rounded animate-pulse my-0.5" />
              ) : (
                <div className="text-xl font-bold font-mono text-sentinel-text tracking-tight">
                  {card.value}
                </div>
              )}
            </div>

            <div className="text-[11px] text-sentinel-muted truncate mt-0.5">
              {card.description}
            </div>
          </div>
        );
      })}
    </div>
  );
};
