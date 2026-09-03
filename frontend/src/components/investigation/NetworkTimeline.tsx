import React, { useState, useEffect, useCallback } from 'react';
import { investigationApi } from '../../api';
import { TimelineResponse, TimelineEvent } from '../../types';
import { Badge } from '../common/Badge';
import { ErrorState } from '../common/ErrorState';
import { EmptyState } from '../common/EmptyState';
import { formatDate, getRiskLevelBadgeVariant } from '../../lib/utils';
import {
  GitFork,
  Clock,
  AlertTriangle,
  FileText,
  Repeat,
  PlusCircle,
  Share2,
  Calendar,
  ArrowRight,
  Phone,
  CreditCard,
  Building,
  RefreshCw,
  Tag,
  Milestone,
} from 'lucide-react';

interface NetworkTimelineProps {
  targetValue: string;
  onSelectEntity: (entityValue: string) => void;
  className?: string;
}

// Normalizes graph node target string by stripping canonical entity prefixes
export const normalizeTargetForTimeline = (rawTarget: string): string => {
  return rawTarget
    .trim()
    .replace(
      /^(phone|upi|email|complaint|organization|person|bankaccount|bank_account|location|url):/i,
      ''
    )
    .trim();
};

export const NetworkTimeline: React.FC<NetworkTimelineProps> = ({
  targetValue,
  onSelectEntity,
  className = '',
}) => {
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'events' | 'entities' | 'milestones'>('events');

  const fetchTimeline = useCallback(async () => {
    if (!targetValue) return;

    setLoading(true);
    setError(null);
    setTimeline(null); // Clear previous timeline data immediately

    try {
      const cleanTarget = normalizeTargetForTimeline(targetValue);
      const data = await investigationApi.getTimeline(cleanTarget);
      setTimeline(data);
    } catch (err: any) {
      setError(
        err.message ||
          `Failed to reconstruct timeline for target "${targetValue}".`
      );
    } finally {
      setLoading(false);
    }
  }, [targetValue]);

  useEffect(() => {
    fetchTimeline();
  }, [fetchTimeline]);

  // Helper to compute time span duration
  const formatTimeSpan = (start?: string | null, end?: string | null) => {
    if (!start || !end) return null;
    try {
      const s = new Date(start).getTime();
      const e = new Date(end).getTime();
      const diffMs = Math.abs(e - s);
      const mins = Math.round(diffMs / (1000 * 60));
      if (mins < 60) return `${mins}m duration`;
      const hrs = Math.floor(mins / 60);
      const remMins = mins % 60;
      if (hrs < 24) return `${hrs}h ${remMins}m duration`;
      const days = Math.round(hrs / 24);
      return `${days}d duration`;
    } catch {
      return null;
    }
  };

  // Event type visual styling configuration
  const getEventStyle = (eventType: string) => {
    switch (eventType?.toUpperCase()) {
      case 'COMPLAINT_CREATED':
        return {
          icon: FileText,
          badgeText: 'CASE REGISTERED',
          badgeVariant: 'info' as const,
          borderColor: 'border-blue-900/60',
          dotColor: 'bg-blue-400',
          textColor: 'text-blue-400',
        };
      case 'ENTITY_FIRST_SEEN':
        return {
          icon: PlusCircle,
          badgeText: 'INCEPTION',
          badgeVariant: 'success' as const,
          borderColor: 'border-emerald-900/60',
          dotColor: 'bg-emerald-400',
          textColor: 'text-emerald-400',
        };
      case 'ENTITY_REUSED':
        return {
          icon: Repeat,
          badgeText: 'REUSED IDENTIFIER',
          badgeVariant: 'warning' as const,
          borderColor: 'border-amber-900/60',
          dotColor: 'bg-amber-400',
          textColor: 'text-amber-400',
        };
      case 'NETWORK_EXPANDED':
        return {
          icon: Share2,
          badgeText: 'EXPANSION',
          badgeVariant: 'neutral' as const,
          borderColor: 'border-purple-900/60',
          dotColor: 'bg-purple-400',
          textColor: 'text-purple-400',
        };
      default:
        return {
          icon: Clock,
          badgeText: eventType || 'EVENT',
          badgeVariant: 'neutral' as const,
          borderColor: 'border-sentinel-border',
          dotColor: 'bg-slate-400',
          textColor: 'text-slate-400',
        };
    }
  };

  // Entity type icon helper
  const getEntityIcon = (type: string) => {
    const t = type?.toLowerCase();
    if (t?.includes('phone')) return Phone;
    if (t?.includes('upi')) return CreditCard;
    if (t?.includes('org')) return Building;
    return Tag;
  };

  return (
    <div
      className={`rounded-lg bg-sentinel-surface border border-sentinel-border overflow-hidden ${className}`}
    >
      {/* 1. Header: Title, Target, Scope, and Time Span */}
      <div className="p-3.5 border-b border-sentinel-border bg-sentinel-surface flex flex-col sm:flex-row sm:items-center justify-between gap-3 select-none">
        <div className="flex items-center gap-2">
          <GitFork className="w-4 h-4 text-purple-400" />
          <h3 className="text-xs font-bold font-mono uppercase text-sentinel-text tracking-wider">
            Network Evolution
          </h3>
          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-sentinel-bg border border-sentinel-border text-sentinel-dim truncate max-w-xs">
            TARGET: {normalizeTargetForTimeline(targetValue)}
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-purple-950/40 border border-purple-800/40 text-purple-300 hidden md:inline-block">
            Deterministic Timeline
          </span>
        </div>

        {/* Refresh & Summary Counters */}
        <div className="flex items-center gap-2">
          {timeline && (
            <div className="flex items-center gap-2 text-[10px] font-mono text-sentinel-dim">
              <span>{timeline.total_events} events</span>
              {formatTimeSpan(timeline.start_time, timeline.end_time) && (
                <>
                  <span>•</span>
                  <span className="text-amber-400">
                    {formatTimeSpan(timeline.start_time, timeline.end_time)}
                  </span>
                </>
              )}
            </div>
          )}

          <button
            onClick={fetchTimeline}
            disabled={loading}
            title="Reload Timeline"
            className="p-1 rounded bg-sentinel-bg hover:bg-sentinel-surfaceHover border border-sentinel-border text-sentinel-muted hover:text-sentinel-text transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* 2. Main Body */}
      <div className="p-4 space-y-4">
        {loading ? (
          <div className="space-y-3">
            <div className="h-8 bg-sentinel-surfaceHover rounded animate-pulse" />
            <div className="space-y-2 pt-2">
              {[...Array(4)].map((_, i) => (
                <div
                  key={i}
                  className="h-14 bg-sentinel-surfaceHover rounded animate-pulse"
                />
              ))}
            </div>
          </div>
        ) : error ? (
          <ErrorState
            title="Timeline Reconstruction Failed"
            message={error}
            onRetry={fetchTimeline}
          />
        ) : !timeline || timeline.total_events === 0 ? (
          <EmptyState
            title="No chronological events recorded"
            message={`No connected complaints or historical interaction milestones found for target "${targetValue}".`}
          />
        ) : (
          <>
            {/* Summary Statistics Strip (Complaints, Phones, UPIs, Orgs) */}
            {timeline.statistics && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <div className="p-2 rounded bg-sentinel-bg border border-sentinel-border flex items-center justify-between">
                  <div className="text-[10px] font-mono text-sentinel-dim uppercase">
                    Complaints
                  </div>
                  <div className="font-mono text-xs font-bold text-sentinel-text">
                    {timeline.statistics.total_complaints}
                  </div>
                </div>

                <div className="p-2 rounded bg-sentinel-bg border border-sentinel-border flex items-center justify-between">
                  <div className="text-[10px] font-mono text-sentinel-dim uppercase">
                    Phones
                  </div>
                  <div className="font-mono text-xs font-bold text-blue-400">
                    {timeline.statistics.phones}
                  </div>
                </div>

                <div className="p-2 rounded bg-sentinel-bg border border-sentinel-border flex items-center justify-between">
                  <div className="text-[10px] font-mono text-sentinel-dim uppercase">
                    UPI Handles
                  </div>
                  <div className="font-mono text-xs font-bold text-emerald-400">
                    {timeline.statistics.upis}
                  </div>
                </div>

                <div className="p-2 rounded bg-sentinel-bg border border-sentinel-border flex items-center justify-between">
                  <div className="text-[10px] font-mono text-sentinel-dim uppercase">
                    Organizations
                  </div>
                  <div className="font-mono text-xs font-bold text-purple-400">
                    {timeline.statistics.organizations}
                  </div>
                </div>
              </div>
            )}

            {/* 3. Deterministic Risk Signals Strip (timeline.insights) */}
            {timeline.insights && timeline.insights.length > 0 && (
              <div className="p-3 rounded-lg bg-sentinel-bg/80 border border-sentinel-border space-y-2">
                <div className="flex items-center gap-1.5 text-xs font-mono uppercase tracking-wider text-sentinel-text font-semibold">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                  <span>Timeline Risk Signals</span>
                  <span className="text-[10px] text-sentinel-dim font-normal">
                    ({timeline.insights.length} deterministic findings)
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {timeline.insights.map((insight, idx) => (
                    <div
                      key={idx}
                      className="p-2.5 rounded bg-sentinel-surface border border-sentinel-border flex items-start gap-2"
                    >
                      <Badge
                        variant={getRiskLevelBadgeVariant(insight.severity)}
                        size="sm"
                      >
                        {insight.severity}
                      </Badge>
                      <div className="text-xs">
                        <span className="font-mono font-bold text-sentinel-text mr-1">
                          {insight.title}:
                        </span>
                        <span className="text-sentinel-muted">
                          {insight.description}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 4. Tab Switcher: Events vs. Entity Reuse vs. Milestones */}
            <div className="flex items-center justify-between border-b border-sentinel-border pt-1">
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setActiveTab('events')}
                  className={`px-3 py-1.5 text-xs font-mono font-medium transition-colors border-b-2 -mb-px flex items-center gap-1.5 ${
                    activeTab === 'events'
                      ? 'border-purple-400 text-purple-300'
                      : 'border-transparent text-sentinel-dim hover:text-sentinel-text'
                  }`}
                >
                  <Calendar className="w-3.5 h-3.5" />
                  <span>Chronological Events ({timeline.events.length})</span>
                </button>

                <button
                  onClick={() => setActiveTab('entities')}
                  className={`px-3 py-1.5 text-xs font-mono font-medium transition-colors border-b-2 -mb-px flex items-center gap-1.5 ${
                    activeTab === 'entities'
                      ? 'border-purple-400 text-purple-300'
                      : 'border-transparent text-sentinel-dim hover:text-sentinel-text'
                  }`}
                >
                  <Repeat className="w-3.5 h-3.5" />
                  <span>
                    Entity Inception & Reuse (
                    {timeline.entity_first_seen?.length || 0})
                  </span>
                </button>

                {timeline.fraud_evolution &&
                  timeline.fraud_evolution.length > 0 && (
                    <button
                      onClick={() => setActiveTab('milestones')}
                      className={`px-3 py-1.5 text-xs font-mono font-medium transition-colors border-b-2 -mb-px flex items-center gap-1.5 ${
                        activeTab === 'milestones'
                          ? 'border-purple-400 text-purple-300'
                          : 'border-transparent text-sentinel-dim hover:text-sentinel-text'
                      }`}
                    >
                      <Milestone className="w-3.5 h-3.5" />
                      <span>
                        Milestones ({timeline.fraud_evolution.length})
                      </span>
                    </button>
                  )}
              </div>
            </div>

            {/* Tab Content 1: Chronological Event Timeline */}
            {activeTab === 'events' && (
              <div className="relative pl-6 space-y-4 pt-2 before:absolute before:left-2 before:top-3 before:bottom-3 before:w-0.5 before:bg-sentinel-border">
                {timeline.events.map((evt: TimelineEvent, idx: number) => {
                  const style = getEventStyle(evt.event_type);
                  const Icon = style.icon;

                  return (
                    <div key={idx} className="relative group">
                      {/* Timeline dot */}
                      <div
                        className={`absolute -left-6 top-1.5 w-3 h-3 rounded-full border-2 border-sentinel-surface ${style.dotColor}`}
                      />

                      <div className="p-3 rounded-lg bg-sentinel-bg border border-sentinel-border hover:border-sentinel-borderLight transition-all">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 mb-1">
                          <div className="flex items-center gap-2">
                            <span className="p-1 rounded bg-sentinel-surface border border-sentinel-border text-sentinel-muted">
                              <Icon className="w-3 h-3" />
                            </span>
                            <span className="text-xs font-bold font-mono text-sentinel-text">
                              {evt.title}
                            </span>
                          </div>

                          <div className="flex items-center gap-2">
                            <Badge variant={style.badgeVariant} size="sm">
                              {style.badgeText}
                            </Badge>
                            <span className="text-[10px] font-mono text-sentinel-dim">
                              {formatDate(evt.timestamp)}
                            </span>
                          </div>
                        </div>

                        {evt.description && (
                          <p className="text-xs text-sentinel-muted mt-1 leading-relaxed">
                            {evt.description}
                          </p>
                        )}

                        {/* Event Metadata: complaint_id or lookup values */}
                        {(() => {
                          const meta = evt.metadata;
                          if (!meta || Object.keys(meta).length === 0) return null;
                          return (
                            <div className="pt-2 mt-2 border-t border-sentinel-border/50 flex flex-wrap items-center gap-1.5 text-[10px] font-mono text-sentinel-dim">
                              {meta.complaint_id && (
                                <span className="px-1.5 py-0.5 rounded bg-sentinel-surface border border-sentinel-border text-blue-300">
                                  CASE: {String(meta.complaint_id).slice(0, 8)}
                                </span>
                              )}
                              {meta.lookup_value && (
                                <button
                                  onClick={() =>
                                    onSelectEntity(String(meta.lookup_value))
                                  }
                                  className="px-1.5 py-0.5 rounded bg-sentinel-surface hover:bg-sentinel-surfaceHover border border-sentinel-border text-sentinel-text hover:text-blue-400 transition-colors cursor-pointer inline-flex items-center gap-1"
                                  title="Pivot investigation to this entity"
                                >
                                  <span>{String(meta.lookup_value)}</span>
                                  <ArrowRight className="w-2.5 h-2.5 opacity-60" />
                                </button>
                              )}
                            </div>
                          );
                        })()}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Tab Content 2: Entity Inception & Reuse Tracker */}
            {activeTab === 'entities' && (
              <div className="space-y-2 pt-1">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                  {timeline.entity_first_seen?.map((ent, idx) => {
                    const EntityIcon = getEntityIcon(ent.entity_type);

                    return (
                      <div
                        key={idx}
                        className="p-3 rounded-lg bg-sentinel-bg border border-sentinel-border flex flex-col justify-between"
                      >
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <div className="flex items-center gap-2">
                            <div className="p-1.5 rounded bg-sentinel-surface border border-sentinel-border text-purple-400">
                              <EntityIcon className="w-3.5 h-3.5" />
                            </div>
                            <div>
                              <button
                                onClick={() => onSelectEntity(ent.entity_value)}
                                className="font-mono text-xs font-bold text-sentinel-text hover:text-blue-400 transition-colors text-left truncate max-w-[200px] flex items-center gap-1 group cursor-pointer"
                                title="Pivot to this target"
                              >
                                <span>{ent.entity_value}</span>
                                <ArrowRight className="w-2.5 h-2.5 opacity-40 group-hover:opacity-100" />
                              </button>
                              <span className="text-[10px] font-mono text-sentinel-dim uppercase">
                                {ent.entity_type}
                              </span>
                            </div>
                          </div>

                          <Badge
                            variant={ent.usage_count > 3 ? 'danger' : 'warning'}
                            size="sm"
                          >
                            {ent.usage_count} {ent.usage_count === 1 ? 'CASE' : 'CASES'}
                          </Badge>
                        </div>

                        <div className="pt-2 border-t border-sentinel-border/50 flex items-center justify-between text-[10px] font-mono text-sentinel-dim">
                          <span>First seen: {formatDate(ent.first_seen)}</span>
                          <span className="truncate max-w-[120px]">
                            Origin: {ent.first_seen_complaint?.slice(0, 8)}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Tab Content 3: Fraud Network Evolution Milestones */}
            {activeTab === 'milestones' && timeline.fraud_evolution && (
              <div className="space-y-2 pt-1">
                {timeline.fraud_evolution.map((m, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-sentinel-bg border border-purple-900/40 flex items-start gap-3"
                  >
                    <div className="p-1.5 rounded bg-purple-950/60 border border-purple-800/80 text-purple-300 shrink-0 mt-0.5">
                      <Milestone className="w-3.5 h-3.5" />
                    </div>
                    <div className="flex-1">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-1">
                        <span className="text-xs font-bold font-mono text-sentinel-text">
                          {m.title}
                        </span>
                        <span className="text-[10px] font-mono text-sentinel-dim">
                          {formatDate(m.timestamp)}
                        </span>
                      </div>
                      <p className="text-xs text-sentinel-muted leading-relaxed">
                        {m.description}
                      </p>

                      {/* Related Entities */}
                      {m.related_entities && m.related_entities.length > 0 && (
                        <div className="pt-2 mt-2 border-t border-purple-900/30 flex flex-wrap items-center gap-1">
                          <span className="text-[10px] font-mono text-sentinel-dim mr-1">
                            Associated:
                          </span>
                          {m.related_entities.map((entity, eIdx) => (
                            <button
                              key={eIdx}
                              onClick={() => onSelectEntity(entity)}
                              className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-sentinel-surface hover:bg-sentinel-surfaceHover border border-sentinel-border text-purple-300 transition-colors"
                              title="Pivot to target"
                            >
                              {entity}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
