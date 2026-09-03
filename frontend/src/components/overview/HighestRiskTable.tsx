import React from 'react';
import { TopRiskEntityResponse } from '../../types';
import { Badge } from '../common/Badge';
import { ErrorState } from '../common/ErrorState';
import { EmptyState } from '../common/EmptyState';
import { getRiskLevelBadgeVariant } from '../../lib/utils';
import { ShieldAlert, ArrowUpRight, Phone, CreditCard, Mail, Building2, User, Globe, MapPin, Tag } from 'lucide-react';

interface HighestRiskTableProps {
  data: TopRiskEntityResponse[] | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  onSelectEntity?: (entityValue: string) => void;
}

export const HighestRiskTable: React.FC<HighestRiskTableProps> = ({
  data,
  loading,
  error,
  onRetry,
  onSelectEntity,
}) => {
  const getEntityIcon = (label: string) => {
    switch (label.toLowerCase()) {
      case 'phone':
        return <Phone className="w-3.5 h-3.5 text-blue-400" />;
      case 'upi':
        return <CreditCard className="w-3.5 h-3.5 text-emerald-400" />;
      case 'email':
        return <Mail className="w-3.5 h-3.5 text-amber-400" />;
      case 'organization':
        return <Building2 className="w-3.5 h-3.5 text-indigo-400" />;
      case 'person':
        return <User className="w-3.5 h-3.5 text-purple-400" />;
      case 'url':
        return <Globe className="w-3.5 h-3.5 text-cyan-400" />;
      case 'location':
        return <MapPin className="w-3.5 h-3.5 text-rose-400" />;
      default:
        return <Tag className="w-3.5 h-3.5 text-sentinel-dim" />;
    }
  };

  return (
    <div className="rounded-lg bg-sentinel-surface border border-sentinel-border overflow-hidden flex flex-col h-full">
      {/* Table Header */}
      <div className="p-4 border-b border-sentinel-border flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-sentinel-risk-red" />
            <h3 className="text-sm font-semibold text-sentinel-text tracking-wide">
              Highest Risk Entities
            </h3>
            {data && data.length > 0 && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-sentinel-bg border border-sentinel-border text-sentinel-dim">
                TOP {data.length}
              </span>
            )}
          </div>
          <p className="text-[11px] text-sentinel-muted mt-0.5">
            Ranked by multi-identifier co-occurrence, incident volume, and graph centrality
          </p>
        </div>
      </div>

      {/* Content State */}
      <div className="flex-1 overflow-x-auto">
        {loading ? (
          <div className="p-4 space-y-2">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="h-10 rounded bg-sentinel-surfaceHover/50 animate-pulse"
              />
            ))}
          </div>
        ) : error ? (
          <div className="p-6">
            <ErrorState
              title="Unable to load high-risk entities"
              message={error}
              onRetry={onRetry}
            />
          </div>
        ) : !data || data.length === 0 ? (
          <div className="p-6">
            <EmptyState
              title="No high-risk entities detected"
              message="No entity currently exceeds risk baseline thresholds in the active graph cluster."
            />
          </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-sentinel-border bg-sentinel-bg/50 text-[10px] font-mono uppercase text-sentinel-dim">
                <th className="py-2.5 px-4 font-medium">Entity Identifier</th>
                <th className="py-2.5 px-3 font-medium">Type</th>
                <th className="py-2.5 px-3 font-medium">Risk Score</th>
                <th className="py-2.5 px-3 font-medium text-right">Incidents</th>
                <th className="py-2.5 px-3 font-medium text-right">Connections</th>
                <th className="py-2.5 px-3 text-right"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-sentinel-border text-xs">
              {data.map((item, idx) => {
                const entityValue =
                  item.entity.properties?.lookup_value ||
                  item.entity.properties?.value ||
                  item.entity.id;
                const entityType = item.entity.label || 'Entity';

                return (
                  <tr
                    key={item.entity.id || idx}
                    onClick={() => onSelectEntity?.(entityValue)}
                    className="hover:bg-sentinel-surfaceHover/70 cursor-pointer transition-colors group"
                  >
                    <td className="py-2.5 px-4 font-mono text-sentinel-text font-medium">
                      <div className="flex items-center gap-2 truncate max-w-xs">
                        <span className="text-sentinel-dim text-[11px] font-normal w-4">
                          #{idx + 1}
                        </span>
                        <span className="truncate group-hover:text-blue-400 transition-colors">
                          {entityValue}
                        </span>
                      </div>
                    </td>

                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-1.5 text-sentinel-muted text-[11px]">
                        {getEntityIcon(entityType)}
                        <span>{entityType}</span>
                      </div>
                    </td>

                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-2">
                        <Badge variant={getRiskLevelBadgeVariant(item.risk_level)}>
                          {item.risk_level}
                        </Badge>
                        <span className="font-mono text-[11px] text-sentinel-dim">
                          {item.risk_score}/100
                        </span>
                      </div>
                    </td>

                    <td className="py-2.5 px-3 text-right font-mono font-medium text-sentinel-text">
                      {item.incident_count}
                    </td>

                    <td className="py-2.5 px-3 text-right font-mono text-sentinel-muted">
                      {item.neighbor_count}
                    </td>

                    <td className="py-2.5 px-3 text-right">
                      <button
                        title="Investigate target"
                        className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded bg-sentinel-bg border border-sentinel-border text-sentinel-muted hover:text-white"
                      >
                        <ArrowUpRight className="w-3.5 h-3.5 text-blue-400" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
