import React from 'react';
import { IncidentListResponse } from '../../types';
import { Badge } from '../common/Badge';
import { ErrorState } from '../common/ErrorState';
import { EmptyState } from '../common/EmptyState';
import {
  formatDate,
  getPriorityBadgeVariant,
  getRiskLevelBadgeVariant,
  getStatusBadgeVariant,
} from '../../lib/utils';
import { FileText } from 'lucide-react';

interface RecentComplaintsTableProps {
  data: IncidentListResponse[] | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  onSelectComplaint?: (complaintId: string) => void;
}

export const RecentComplaintsTable: React.FC<RecentComplaintsTableProps> = ({
  data,
  loading,
  error,
  onRetry,
  onSelectComplaint,
}) => {
  return (
    <div className="rounded-lg bg-sentinel-surface border border-sentinel-border overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-sentinel-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-blue-400" />
          <h3 className="text-sm font-semibold text-sentinel-text tracking-wide">
            Recent Fraud Complaints
          </h3>
          {data && data.length > 0 && (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-sentinel-bg border border-sentinel-border text-sentinel-dim">
              {data.length} INGESTED
            </span>
          )}
        </div>
        <p className="text-[11px] text-sentinel-muted">
          Chronological feed of citizen & institution reported incidents
        </p>
      </div>

      {/* Content */}
      <div className="overflow-x-auto">
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
              title="Unable to load recent complaints"
              message={error}
              onRetry={onRetry}
            />
          </div>
        ) : !data || data.length === 0 ? (
          <div className="p-6">
            <EmptyState
              title="No complaints have been reported"
              message="No incident records were found in the database."
            />
          </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-sentinel-border bg-sentinel-bg/50 text-[10px] font-mono uppercase text-sentinel-dim">
                <th className="py-2.5 px-4 font-medium">Case Reference</th>
                <th className="py-2.5 px-4 font-medium">Title</th>
                <th className="py-2.5 px-3 font-medium">Status</th>
                <th className="py-2.5 px-3 font-medium">Priority</th>
                <th className="py-2.5 px-3 font-medium">Risk Score</th>
                <th className="py-2.5 px-4 font-medium text-right">Reported At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-sentinel-border text-xs">
              {data.map((item) => {
                const caseRef = item.case_reference || `CASE-${item.id.slice(0, 8).toUpperCase()}`;
                const hasScore = item.risk_score !== null && item.risk_score !== undefined;
                const riskLevel = hasScore
                  ? (item.risk_score as number) >= 0.7
                    ? 'HIGH'
                    : (item.risk_score as number) >= 0.4
                    ? 'MEDIUM'
                    : 'LOW'
                  : null;

                return (
                  <tr
                    key={item.id}
                    onClick={() => onSelectComplaint?.(item.id)}
                    className="hover:bg-sentinel-surfaceHover/70 transition-colors cursor-pointer"
                  >
                    <td className="py-2.5 px-4 font-mono text-[11px] text-blue-400 font-medium">
                      {caseRef}
                    </td>

                    <td className="py-2.5 px-4 font-medium text-sentinel-text max-w-md truncate">
                      <div className="truncate" title={item.title}>
                        {item.title}
                      </div>
                    </td>

                    <td className="py-2.5 px-3">
                      <Badge variant={getStatusBadgeVariant(item.status)}>
                        {item.status.replace('_', ' ')}
                      </Badge>
                    </td>

                    <td className="py-2.5 px-3">
                      <Badge variant={getPriorityBadgeVariant(item.priority)}>
                        {item.priority}
                      </Badge>
                    </td>

                    <td className="py-2.5 px-3">
                      {hasScore ? (
                        <div className="flex items-center gap-1.5 font-mono text-[11px]">
                          <Badge variant={getRiskLevelBadgeVariant(riskLevel)}>
                            {riskLevel}
                          </Badge>
                          <span className="text-sentinel-dim">
                            {Math.round((item.risk_score as number) * 100)}%
                          </span>
                        </div>
                      ) : (
                        <span className="text-[11px] font-mono text-sentinel-dim italic">
                          Unscored
                        </span>
                      )}
                    </td>

                    <td className="py-2.5 px-4 text-right font-mono text-[11px] text-sentinel-muted whitespace-nowrap">
                      {formatDate(item.created_at)}
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
