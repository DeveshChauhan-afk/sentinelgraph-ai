import React from 'react';
import { TopConnectedEntity } from '../../types';
import { ErrorState } from '../common/ErrorState';
import { EmptyState } from '../common/EmptyState';
import { Network, ArrowUpRight, Share2, Layers } from 'lucide-react';

interface FraudHubsListProps {
  data: TopConnectedEntity[] | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  onSelectEntity?: (entityValue: string) => void;
}

export const FraudHubsList: React.FC<FraudHubsListProps> = ({
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
            <Network className="w-4 h-4 text-purple-400" />
            <h3 className="text-xs font-semibold text-sentinel-text uppercase font-mono tracking-wide">
              Fraud Hubs (Centrality)
            </h3>
          </div>
          <p className="text-[11px] text-sentinel-muted mt-0.5">
            Top nodes connecting disparate fraud rings
          </p>
        </div>
      </div>

      {/* Content */}
      <div className="p-2 divide-y divide-sentinel-border/50">
        {loading ? (
          <div className="p-3 space-y-2">
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="h-10 rounded bg-sentinel-surfaceHover/50 animate-pulse"
              />
            ))}
          </div>
        ) : error ? (
          <div className="p-4">
            <ErrorState
              title="Unable to load fraud hubs"
              message={error}
              onRetry={onRetry}
            />
          </div>
        ) : !data || data.length === 0 ? (
          <div className="p-4">
            <EmptyState
              title="No hub nodes identified"
              message="No entity currently bridges multiple sub-graphs."
            />
          </div>
        ) : (
          data.slice(0, 6).map((item, idx) => (
            <div
              key={item.id || idx}
              onClick={() => onSelectEntity?.(item.label || item.id)}
              className="p-2.5 rounded hover:bg-sentinel-surfaceHover/60 cursor-pointer transition-colors flex items-center justify-between group"
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <span className="w-5 text-[11px] font-mono text-sentinel-dim shrink-0">
                  #{idx + 1}
                </span>

                <div className="min-w-0">
                  <div className="text-xs font-mono text-sentinel-text truncate group-hover:text-blue-400 transition-colors font-medium">
                    {item.label}
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-sentinel-dim mt-0.5">
                    <span className="uppercase font-mono tracking-wider">
                      {item.type}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <div className="text-right">
                  <div className="flex items-center justify-end gap-1 text-xs font-mono font-semibold text-sentinel-text">
                    <Share2 className="w-3 h-3 text-purple-400" />
                    <span>{item.connection_count}</span>
                  </div>
                  <div className="flex items-center justify-end gap-1 text-[10px] font-mono text-sentinel-dim">
                    <Layers className="w-2.5 h-2.5 text-sentinel-dim" />
                    <span>{item.complaint_count} cases</span>
                  </div>
                </div>

                <ArrowUpRight className="w-3.5 h-3.5 text-sentinel-dim group-hover:text-blue-400 transition-colors opacity-0 group-hover:opacity-100" />
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
