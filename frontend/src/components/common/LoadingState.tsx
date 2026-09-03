import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
  description?: string;
  className?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading intelligence...',
  description,
  className = '',
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 text-center rounded-lg border border-sentinel-border bg-sentinel-surface/50 ${className}`}
    >
      <Loader2 className="w-8 h-8 text-sentinel-accent animate-spin mb-3" />
      <div className="text-sm font-medium text-sentinel-text tracking-wide">{message}</div>
      {description && (
        <div className="text-xs text-sentinel-dim mt-1 max-w-sm">{description}</div>
      )}
    </div>
  );
};
