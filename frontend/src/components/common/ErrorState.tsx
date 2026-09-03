import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Unable to retrieve risk intelligence',
  message = 'A connection error occurred while communicating with the intelligence services.',
  onRetry,
  className = '',
}) => {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 text-center rounded-lg border border-sentinel-risk-redBorder bg-sentinel-risk-redBg/20 ${className}`}
    >
      <div className="w-10 h-10 rounded-full bg-sentinel-risk-redBg flex items-center justify-center mb-3 border border-sentinel-risk-redBorder">
        <AlertTriangle className="w-5 h-5 text-sentinel-risk-red" />
      </div>
      <div className="text-sm font-semibold text-sentinel-text mb-1">{title}</div>
      <div className="text-xs text-sentinel-muted max-w-md mb-4">{message}</div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-sentinel-text bg-sentinel-surface hover:bg-sentinel-surfaceHover border border-sentinel-border rounded transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5 text-sentinel-muted" />
          <span>Retry Operation</span>
        </button>
      )}
    </div>
  );
};
