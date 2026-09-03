import React from 'react';
import { SharedEntityAnalysis } from '../../types';
import { ErrorState } from '../common/ErrorState';
import { EmptyState } from '../common/EmptyState';
import { GitFork, ArrowUpRight, Tag } from 'lucide-react';

interface SharedInfrastructureCardProps {
  data: SharedEntityAnalysis[] | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  onSelectEntity?: (entityValue: string) => void;
}

export const SharedInfrastructureCard: React.FC<SharedInfrastructureCardProps> = ({
  data,
  loading,
  error,
  onRetry,
  onSelectEntity,
}) => {
  return (
    <div className="rounded-lg bg-sentinel-surface border border-sentinel-border overflow-hidden flex flex-col">
      {/* Header */}
      <div className="p-3.5 border-b border-sentinel-border flex items-center justify-between">
        <div>
          <div className="flex items-center gap-1.5">
            <GitFork className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs font-semibold text-sentinel-text uppercase font-mono tracking-wide">
              Shared Infrastructure
            </h3>
          </div>
          <p className="text-[11px] text-sentinel-muted mt-0.5">
            One identifier connecting multiple victims/cases
          </p>
        </div>
      </div>

      {/* Content */}
      <div className="p-3 space-y-2.5">
        {loading ? (
          <div className="space-y-2">
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="h-16 rounded bg-sentinel-surfaceHover/50 animate-pulse"
              />
            ))}
          </div>
        ) : error ? (
          <ErrorState
            title="Unable to load shared infrastructure"
            message={error}
            onRetry={onRetry}
          />
        ) : !data || data.length === 0 ? (
          <EmptyState
            title="No shared infrastructure detected"
            message="No identifier has been reused across 2 or more complaints yet."
          />
        ) : (
          data.slice(0, 5).map((item, idx) => (
            <div
              key={item.entity_id || idx}
              onClick={() => onSelectEntity?.(item.entity_label || item.entity_id)}
              className="p-2.5 rounded-lg border border-sentinel-border bg-sentinel-bg/80 hover:border-emerald-700/50 hover:bg-sentinel-surfaceHover/70 cursor-pointer transition-all group"
            >
              {/* Identifier row */}
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 shrink-0" />
                  <span className="font-mono text-xs font-semibold text-sentinel-text truncate group-hover:text-emerald-400 transition-colors">
                    {item.entity_label}
                  </span>
                </div>

                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="text-[10px] font-mono uppercase px-1.5 py-0.2 rounded bg-sentinel-surface border border-sentinel-border text-sentinel-dim">
                    {item.entity_type}
                  </span>
                  <ArrowUpRight className="w-3.5 h-3.5 text-sentinel-dim group-hover:text-emerald-400 transition-colors" />
                </div>
              </div>

              {/* Cross-case bridge indicator */}
              <div className="flex items-center justify-between text-[11px] font-mono text-sentinel-muted pt-1 border-t border-sentinel-border/50">
                <div className="flex items-center gap-1.5 text-emerald-400/90">
                  <GitFork className="w-3 h-3 text-emerald-400" />
                  <span>Linked across {item.complaint_count} complaints</span>
                </div>

                <div className="flex items-center gap-1 text-[10px] text-sentinel-dim">
                  <Tag className="w-2.5 h-2.5" />
                  <span>{item.complaint_ids.length} nodes</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
