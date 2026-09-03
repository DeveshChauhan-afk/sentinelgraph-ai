import React from 'react';
import { NavigationPage } from './Sidebar';
import { ShieldCheck, Database, RefreshCw } from 'lucide-react';

interface HeaderProps {
  currentPage: NavigationPage;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  currentPage,
  onRefresh,
  isRefreshing = false,
}) => {
  const titles: Record<NavigationPage, { title: string; subtitle: string }> = {
    'risk-overview': {
      title: 'Risk Overview',
      subtitle: 'Global Fraud Intelligence Network & Co-occurrence Monitoring',
    },
    investigate: {
      title: 'Investigation',
      subtitle: 'Trace entities, uncover connected fraud rings, and generate evidence-backed intelligence.',
    },
    evaluation: {
      title: 'AI Evaluation & Guardrails',
      subtitle: 'Ground Truth Verification, Anti-Hallucination & Benchmarking',
    },
  };

  const current = titles[currentPage] || titles['risk-overview'];

  return (
    <header className="h-14 border-b border-sentinel-border bg-sentinel-surface px-6 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-4">
        <div>
          <h1 className="text-sm font-semibold text-sentinel-text tracking-wide flex items-center gap-2">
            <span>{current.title}</span>
            <span className="text-sentinel-dim font-mono text-xs font-normal">/</span>
            <span className="text-[11px] font-mono text-sentinel-dim font-normal">
              Track 02: AI Risk Manager
            </span>
          </h1>
          <p className="text-[11px] text-sentinel-muted">{current.subtitle}</p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded bg-sentinel-bg border border-sentinel-border text-[11px] font-mono text-sentinel-muted">
          <Database className="w-3.5 h-3.5 text-blue-400" />
          <span>Neo4j + Postgres + Gemini 3.5</span>
        </div>

        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-950/40 border border-emerald-800/40 text-emerald-400 text-[11px] font-mono">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span>SECURE OPS</span>
        </div>

        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            title="Refresh Intelligence Data"
            className="p-1.5 rounded hover:bg-sentinel-surfaceHover border border-sentinel-border text-sentinel-muted hover:text-sentinel-text transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
        )}
      </div>
    </header>
  );
};
