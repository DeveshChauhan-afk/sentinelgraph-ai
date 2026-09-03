import React from 'react';

export type BadgeVariant = 'danger' | 'warning' | 'success' | 'info' | 'neutral';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'sm',
  className = '',
}) => {
  const variantStyles: Record<BadgeVariant, string> = {
    danger: 'bg-sentinel-risk-redBg text-sentinel-risk-red border-sentinel-risk-redBorder',
    warning: 'bg-sentinel-risk-amberBg text-sentinel-risk-amber border-sentinel-risk-amberBorder',
    success: 'bg-sentinel-risk-greenBg text-sentinel-risk-green border-sentinel-risk-greenBorder',
    info: 'bg-blue-950/60 text-blue-400 border-blue-800/60',
    neutral: 'bg-slate-900/80 text-sentinel-muted border-sentinel-border',
  };

  const sizeStyles = {
    sm: 'text-[10px] px-1.5 py-0.5 font-mono uppercase tracking-wider',
    md: 'text-xs px-2 py-0.5 font-medium',
  };

  return (
    <span
      className={`inline-flex items-center font-semibold rounded border ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
    >
      {children}
    </span>
  );
};
