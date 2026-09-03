import React from 'react';
import {
  ShieldAlert,
  LayoutDashboard,
  Search,
  CheckCircle2,
  Activity,
  Cpu,
} from 'lucide-react';
import { useHealth } from '../hooks/useHealth';

export type NavigationPage = 'risk-overview' | 'investigate' | 'evaluation';

interface SidebarProps {
  currentPage: NavigationPage;
  onNavigate: (page: NavigationPage) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentPage, onNavigate }) => {
  const { health, version, isOnline, loading } = useHealth();

  const navItems: Array<{
    id: NavigationPage;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    tag?: string;
  }> = [
    {
      id: 'risk-overview',
      label: 'Risk Overview',
      icon: LayoutDashboard,
    },
    {
      id: 'investigate',
      label: 'Investigate',
      icon: Search,
    },
    {
      id: 'evaluation',
      label: 'Evaluation',
      icon: CheckCircle2,
    },
  ];

  return (
    <aside className="w-64 flex flex-col h-screen border-r border-sentinel-border bg-sentinel-surface select-none shrink-0">
      {/* Brand Header */}
      <div className="p-4 border-b border-sentinel-border flex items-center gap-3">
        <div className="w-9 h-9 rounded bg-blue-950/60 border border-blue-800/80 flex items-center justify-center shrink-0">
          <ShieldAlert className="w-5 h-5 text-blue-400" />
        </div>
        <div>
          <div className="flex items-center gap-1.5">
            <span className="font-bold tracking-wider text-sm text-sentinel-text font-mono">
              SENTINELGRAPH
            </span>
          </div>
          <div className="text-[10px] uppercase font-mono tracking-widest text-sentinel-dim">
            AI Risk Manager
          </div>
        </div>
      </div>

      {/* Nav Menu */}
      <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-mono uppercase tracking-wider text-sentinel-dim">
          Intelligence Operations
        </div>

        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentPage === item.id;

          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2 text-xs font-medium rounded transition-colors ${
                isActive
                  ? 'bg-sentinel-surfaceHover text-sentinel-text border-l-2 border-sentinel-accent pl-[10px] font-semibold'
                  : 'text-sentinel-muted hover:text-sentinel-text hover:bg-sentinel-surfaceHover/50'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <Icon
                  className={`w-4 h-4 ${
                    isActive ? 'text-sentinel-accent' : 'text-sentinel-dim'
                  }`}
                />
                <span>{item.label}</span>
              </div>
              {item.tag && (
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-sentinel-bg text-sentinel-dim border border-sentinel-border">
                  {item.tag}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer / System Status & Version */}
      <div className="p-3 border-t border-sentinel-border bg-sentinel-bg/60 space-y-2">
        <div className="flex items-center justify-between text-[11px] font-mono">
          <span className="text-sentinel-dim flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-sentinel-dim" />
            System Status
          </span>
          <div className="flex items-center gap-1.5">
            <span
              className={`w-2 h-2 rounded-full ${
                loading
                  ? 'bg-sentinel-dim animate-pulse'
                  : isOnline
                  ? 'bg-sentinel-risk-green'
                  : 'bg-sentinel-risk-red'
              }`}
            />
            <span
              className={`font-medium ${
                isOnline ? 'text-sentinel-risk-green' : 'text-sentinel-risk-red'
              }`}
            >
              {loading ? 'CHECKING' : isOnline ? 'ONLINE' : 'OFFLINE'}
            </span>
          </div>
        </div>

        {health && (
          <div className="grid grid-cols-3 gap-1 text-[9px] font-mono text-sentinel-dim pt-1 border-t border-sentinel-border/50">
            <div className="flex items-center gap-1">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  health.dependencies.postgres?.status === 'HEALTHY'
                    ? 'bg-sentinel-risk-green'
                    : 'bg-sentinel-risk-red'
                }`}
              />
              <span>PG</span>
            </div>
            <div className="flex items-center gap-1">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  health.dependencies.neo4j?.status === 'HEALTHY'
                    ? 'bg-sentinel-risk-green'
                    : 'bg-sentinel-risk-red'
                }`}
              />
              <span>NEO4J</span>
            </div>
            <div className="flex items-center gap-1">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  health.dependencies.gemini?.status === 'HEALTHY'
                    ? 'bg-sentinel-risk-green'
                    : 'bg-sentinel-risk-amber'
                }`}
              />
              <span>GEMINI</span>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between text-[10px] font-mono text-sentinel-dim pt-1">
          <span className="flex items-center gap-1">
            <Cpu className="w-3 h-3 text-sentinel-dim" />
            API Core
          </span>
          <span>v{version}</span>
        </div>
      </div>
    </aside>
  );
};
