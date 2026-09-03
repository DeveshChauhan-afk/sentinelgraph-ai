import React from 'react';
import { Database } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  message?: string;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No entities found',
  message = 'There are no intelligence records matching the selected parameters or time window.',
  action,
  className = '',
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 text-center rounded-lg border border-sentinel-border border-dashed bg-sentinel-surface/30 ${className}`}
    >
      <div className="w-10 h-10 rounded-full bg-sentinel-surface flex items-center justify-center mb-3 border border-sentinel-border">
        <Database className="w-5 h-5 text-sentinel-dim" />
      </div>
      <div className="text-sm font-medium text-sentinel-text mb-1">{title}</div>
      <div className="text-xs text-sentinel-muted max-w-sm mb-4">{message}</div>
      {action && <div>{action}</div>}
    </div>
  );
};
