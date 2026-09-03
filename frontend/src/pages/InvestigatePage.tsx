import React, { useState, useEffect } from 'react';
import {
  Search,
  Phone,
  CreditCard,
  Mail,
  FileText,
  Sparkles,
  ArrowRight,
  ShieldAlert,
  Info,
  CheckCircle2,
  X,
  Crosshair,
  Compass,
  Network,
  GitFork,
} from 'lucide-react';
import { Badge } from '../components/common/Badge';
import { GraphVisualization } from '../components/investigation/GraphVisualization';
import { RiskIntelligencePanel } from '../components/investigation/RiskIntelligencePanel';
import { NetworkTimeline } from '../components/investigation/NetworkTimeline';
import { AiInvestigationDossier } from '../components/investigation/AiInvestigationDossier';
import { investigationApi } from '../api';
import { ProfessionalInvestigationReport, InvestigationTargetType } from '../types';

interface InvestigatePageProps {
  targetEntity?: string | null;
}

interface DemoPreset {
  value: string;
  displayValue?: string;
  label: string;
  type: string;
  icon: React.ComponentType<{ className?: string }>;
}

const DEMO_PRESETS: DemoPreset[] = [
  {
    value: '+919876543210',
    displayValue: '+91 9876543210',
    label: 'Ring Alpha • KYC Scam',
    type: 'Phone',
    icon: Phone,
  },
  {
    value: 'securekyc@ibl',
    displayValue: 'securekyc@ibl',
    label: 'Ring Alpha • UPI Mule',
    type: 'UPI',
    icon: CreditCard,
  },
  {
    value: '+919988776655',
    displayValue: '+91 9988776655',
    label: 'Ring Beta • Marketplace Scam',
    type: 'Phone',
    icon: Phone,
  },
];

export const InvestigatePage: React.FC<InvestigatePageProps> = ({
  targetEntity,
}) => {
  const [inputValue, setInputValue] = useState<string>(targetEntity || '');
  const [selectedTarget, setSelectedTarget] = useState<string | null>(
    targetEntity || null
  );

  // AI Investigation Dossier State
  const [aiReport, setAiReport] = useState<ProfessionalInvestigationReport | null>(null);
  const [loadingAi, setLoadingAi] = useState<boolean>(false);
  const [errorAi, setErrorAi] = useState<string | null>(null);

  // Sync if targetEntity changes from parent navigation
  useEffect(() => {
    if (targetEntity) {
      setInputValue(targetEntity);
      setSelectedTarget(targetEntity);
    }
  }, [targetEntity]);

  // Clear old AI report whenever the investigation target changes
  useEffect(() => {
    setAiReport(null);
    setLoadingAi(false);
    setErrorAi(null);
  }, [selectedTarget]);

  const handleSelectPreset = (presetValue: string) => {
    setInputValue(presetValue);
    setSelectedTarget(presetValue);
  };

  const handleTriggerInvestigation = (e?: React.FormEvent) => {
    if (e) {
      e.preventDefault();
    }
    const trimmed = inputValue.trim();
    if (trimmed) {
      setSelectedTarget(trimmed);
    }
  };

  const scrollToSection = (sectionId: string) => {
    const el = document.getElementById(sectionId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const handleClear = () => {
    setInputValue('');
    setSelectedTarget(null);
  };

  // Helper to map identifier to backend InvestigationTargetType
  const mapToApiTargetType = (val: string): InvestigationTargetType => {
    const trimmed = val.trim();
    if (trimmed.startsWith('+') || /^\d{10}$/.test(trimmed.replace(/\s+/g, ''))) {
      return 'phone';
    }
    if (trimmed.includes('@') && !trimmed.includes('.')) {
      return 'upi';
    }
    if (trimmed.includes('@') && trimmed.includes('.')) {
      return 'email';
    }
    if (
      trimmed.toLowerCase().startsWith('case-') ||
      trimmed.toLowerCase().startsWith('complaint:') ||
      /^[0-9a-f]{8}-[0-9a-f]{4}/i.test(trimmed)
    ) {
      return 'complaint';
    }
    return 'phone';
  };

  const handleGenerateAi = async () => {
    if (!selectedTarget || loadingAi) return;

    setLoadingAi(true);
    setErrorAi(null);

    try {
      const apiType = mapToApiTargetType(selectedTarget);
      // Strip any node prefix if present
      const cleanValue = selectedTarget.replace(/^(phone|upi|email|complaint):/i, '').trim();

      const report = await investigationApi.generateReport({
        target_type: apiType,
        target_value: cleanValue,
      });
      setAiReport(report);
    } catch (err: any) {
      setErrorAi(
        err.message ||
          'Failed to generate AI investigation dossier. Please check Gemini connection and retry.'
      );
    } finally {
      setLoadingAi(false);
    }
  };

  // Helper to infer entity format for UI display
  const inferTargetType = (val: string): string => {
    const trimmed = val.trim();
    if (trimmed.startsWith('+') || /^\d{10}$/.test(trimmed.replace(/\s+/g, ''))) {
      return 'Phone';
    }
    if (trimmed.includes('@') && !trimmed.includes('.')) {
      return 'UPI';
    }
    if (trimmed.includes('@') && trimmed.includes('.')) {
      return 'Email';
    }
    if (trimmed.toLowerCase().startsWith('case-') || trimmed.toLowerCase().startsWith('complaint:')) {
      return 'Complaint';
    }
    return 'Entity Identifier';
  };

  const isButtonDisabled = !inputValue.trim();

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* 1. Page Header */}
      <div className="border-b border-sentinel-border pb-4">
        <div className="flex items-center gap-2 mb-1">
          <Crosshair className="w-5 h-5 text-sentinel-accent" />
          <h2 className="text-lg font-bold text-sentinel-text tracking-tight font-mono uppercase">
            Investigation
          </h2>
          <Badge variant="info">TARGET SELECTION</Badge>
        </div>
        <p className="text-xs text-sentinel-muted">
          Trace entities, uncover connected fraud rings, and generate evidence-backed intelligence.
        </p>
      </div>

      {/* 2. Main Search & Target Input Card */}
      <div className="rounded-lg bg-sentinel-surface border border-sentinel-border p-5 shadow-sm">
        <form onSubmit={handleTriggerInvestigation} className="space-y-4">
          <label
            htmlFor="investigation-input"
            className="block text-xs font-mono uppercase text-sentinel-dim font-medium tracking-wider"
          >
            Target Identifier
          </label>

          <div className="relative flex items-center">
            <div className="absolute left-3.5 text-sentinel-dim pointer-events-none flex items-center">
              <Search className="w-5 h-5 text-sentinel-dim" />
            </div>

            <input
              id="investigation-input"
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Enter phone (+91...), UPI handle (user@bank), email, or complaint ID..."
              className="w-full pl-11 pr-24 py-3 bg-sentinel-bg border border-sentinel-border rounded-lg text-sm text-sentinel-text placeholder-sentinel-dim font-mono focus:outline-none focus:border-sentinel-accent focus:ring-1 focus:ring-sentinel-accent transition-all"
              autoComplete="off"
              spellCheck="false"
            />

            {inputValue && (
              <button
                type="button"
                onClick={handleClear}
                className="absolute right-28 p-1 text-sentinel-dim hover:text-sentinel-text transition-colors"
                title="Clear input"
              >
                <X className="w-4 h-4" />
              </button>
            )}

            <button
              type="submit"
              disabled={isButtonDisabled}
              className={`absolute right-1.5 px-4 py-2 text-xs font-medium rounded transition-all flex items-center gap-1.5 ${
                isButtonDisabled
                  ? 'bg-slate-800 text-slate-500 border border-slate-700/50 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-500 text-white border border-blue-400/40 shadow-sm cursor-pointer'
              }`}
            >
              <span>Investigate</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </form>

        {/* 3. Demo Target Presets */}
        <div className="mt-5 pt-4 border-t border-sentinel-border">
          <div className="flex items-center gap-2 mb-2.5">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-[11px] font-mono uppercase tracking-wider text-sentinel-dim">
              Demo Target Presets
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            {DEMO_PRESETS.map((preset) => {
              const Icon = preset.icon;
              const isCurrent = inputValue === preset.value;

              return (
                <button
                  key={preset.value}
                  type="button"
                  onClick={() => handleSelectPreset(preset.value)}
                  className={`p-2.5 rounded border text-left transition-all flex items-start justify-between group ${
                    isCurrent
                      ? 'bg-sentinel-surfaceHover border-sentinel-accent/80 ring-1 ring-sentinel-accent/40'
                      : 'bg-sentinel-bg/80 border-sentinel-border hover:border-sentinel-borderLight hover:bg-sentinel-surfaceHover/50'
                  }`}
                >
                  <div className="min-w-0 pr-2">
                    <div className="font-mono text-xs font-semibold text-sentinel-text group-hover:text-blue-400 transition-colors truncate">
                      {preset.displayValue || preset.value}
                    </div>
                    <div className="text-[11px] text-sentinel-muted mt-0.5 truncate">
                      {preset.label}
                    </div>
                  </div>

                  <div className="p-1 rounded bg-sentinel-surface border border-sentinel-border shrink-0 mt-0.5 text-sentinel-dim group-hover:text-blue-400 transition-colors">
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* 4. Active Target Status Card (Target Armed) */}
      {selectedTarget ? (
        <div className="rounded-lg bg-sentinel-surface border border-blue-900/60 p-4 relative overflow-hidden">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded bg-blue-950/70 border border-blue-800/80 flex items-center justify-center shrink-0 text-blue-400">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono uppercase tracking-wider text-blue-400 font-semibold">
                    Target Armed
                  </span>
                  <Badge variant="info">{inferTargetType(selectedTarget)}</Badge>
                </div>
                <div className="font-mono text-sm font-bold text-sentinel-text mt-0.5">
                  {selectedTarget}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-blue-950/40 border border-blue-800/40 text-[11px] font-mono text-blue-300">
                <CheckCircle2 className="w-3.5 h-3.5 text-blue-400" />
                <span>Ready for Graph Traversal</span>
              </span>

              <button
                onClick={handleClear}
                className="px-2.5 py-1 rounded bg-sentinel-bg hover:bg-sentinel-surfaceHover border border-sentinel-border text-[11px] font-mono text-sentinel-muted hover:text-sentinel-text transition-colors"
              >
                Reset
              </button>
            </div>
          </div>

          <div className="mt-3 pt-3 border-t border-sentinel-border/60 text-xs text-sentinel-dim flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 shrink-0 text-blue-400" />
            <span>
              Target selected. Generating multi-hop fraud network traversal and cross-entity intelligence.
            </span>
          </div>
        </div>
      ) : null}

      {/* 5. Graph, Risk, Timeline & AI Investigation Workspace (Rendered when target is selected) */}
      {selectedTarget ? (
        <div className="space-y-6">
          {/* Sticky Workspace Jump Bar */}
          <div className="sticky top-0 z-20 bg-sentinel-surface/95 backdrop-blur-md py-2 px-3.5 rounded-lg border border-sentinel-border shadow-lg flex flex-wrap items-center justify-between gap-2 select-none">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono uppercase tracking-wider text-sentinel-dim flex items-center gap-1">
                <Compass className="w-3.5 h-3.5 text-blue-400" />
                <span>Workspace:</span>
              </span>
              <span className="font-mono text-xs font-bold text-sentinel-text truncate max-w-[200px]">
                {selectedTarget}
              </span>
            </div>

            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => scrollToSection('section-graph')}
                className="px-2.5 py-1 rounded bg-sentinel-bg hover:bg-sentinel-surfaceHover border border-sentinel-border text-xs font-mono text-sentinel-dim hover:text-blue-400 transition-colors flex items-center gap-1.5 cursor-pointer"
                title="Jump to Graph Visualization"
              >
                <Network className="w-3 h-3 text-blue-400" />
                <span>Graph</span>
              </button>
              <button
                type="button"
                onClick={() => scrollToSection('section-risk')}
                className="px-2.5 py-1 rounded bg-sentinel-bg hover:bg-sentinel-surfaceHover border border-sentinel-border text-xs font-mono text-sentinel-dim hover:text-amber-400 transition-colors flex items-center gap-1.5 cursor-pointer"
                title="Jump to Risk Intelligence"
              >
                <ShieldAlert className="w-3 h-3 text-amber-400" />
                <span>Risk</span>
              </button>
              <button
                type="button"
                onClick={() => scrollToSection('section-timeline')}
                className="px-2.5 py-1 rounded bg-sentinel-bg hover:bg-sentinel-surfaceHover border border-sentinel-border text-xs font-mono text-sentinel-dim hover:text-purple-400 transition-colors flex items-center gap-1.5 cursor-pointer"
                title="Jump to Network Evolution Timeline"
              >
                <GitFork className="w-3 h-3 text-purple-400" />
                <span>Timeline</span>
              </button>
              <button
                type="button"
                onClick={() => scrollToSection('section-ai-dossier')}
                className="px-2.5 py-1 rounded bg-sentinel-bg hover:bg-sentinel-surfaceHover border border-sentinel-border text-xs font-mono text-sentinel-dim hover:text-emerald-400 transition-colors flex items-center gap-1.5 cursor-pointer"
                title="Jump to AI Investigation Dossier"
              >
                <Sparkles className="w-3 h-3 text-emerald-400" />
                <span>AI Dossier</span>
              </button>
            </div>
          </div>

          <div id="section-graph" className="scroll-mt-14">
            <GraphVisualization
              targetValue={selectedTarget}
              onSelectNewTarget={handleSelectPreset}
            />
          </div>

          <div id="section-risk" className="scroll-mt-14">
            <RiskIntelligencePanel targetValue={selectedTarget} />
          </div>

          <div id="section-timeline" className="scroll-mt-14">
            <NetworkTimeline
              targetValue={selectedTarget}
              onSelectEntity={handleSelectPreset}
            />
          </div>

          <div id="section-ai-dossier" className="scroll-mt-14">
            <AiInvestigationDossier
              report={aiReport}
              loading={loadingAi}
              error={errorAi}
              onGenerate={handleGenerateAi}
              onRetry={handleGenerateAi}
              onSelectEntity={handleSelectPreset}
              targetValue={selectedTarget}
              hasTarget={Boolean(selectedTarget)}
            />
          </div>
        </div>
      ) : (
        /* Empty Guidance State when no target selected */
        <div className="rounded-lg border border-dashed border-sentinel-border bg-sentinel-surface/30 p-8 text-center">
          <div className="w-10 h-10 rounded-full bg-sentinel-surface border border-sentinel-border flex items-center justify-center mx-auto mb-2 text-sentinel-dim">
            <Crosshair className="w-5 h-5" />
          </div>
          <div className="text-xs font-mono uppercase tracking-wider text-sentinel-dim mb-1">
            Awaiting Target Selection
          </div>
          <div className="text-xs text-sentinel-muted max-w-sm mx-auto">
            Enter an identifier in the search bar above or choose one of the demo presets to reconstruct its fraud network and assess co-occurrence risk.
          </div>
        </div>
      )}

      {/* 5. Explanatory Panel: Investigation targets */}
      <div className="rounded-lg bg-sentinel-surface border border-sentinel-border p-4">
        <div className="flex items-start gap-2.5 mb-3">
          <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
          <div>
            <h3 className="text-xs font-mono uppercase tracking-wider font-semibold text-sentinel-text">
              Investigation targets
            </h3>
            <p className="text-xs text-sentinel-muted mt-0.5">
              Search an entity to reconstruct its connected network and assess risk.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-2 border-t border-sentinel-border">
          <div className="p-2 rounded bg-sentinel-bg/60 border border-sentinel-border flex items-center gap-2">
            <Phone className="w-3.5 h-3.5 text-blue-400 shrink-0" />
            <div>
              <div className="text-[11px] font-medium text-sentinel-text">Phone Numbers</div>
              <div className="text-[10px] font-mono text-sentinel-dim">+91 98765...</div>
            </div>
          </div>

          <div className="p-2 rounded bg-sentinel-bg/60 border border-sentinel-border flex items-center gap-2">
            <CreditCard className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <div>
              <div className="text-[11px] font-medium text-sentinel-text">UPI Handles</div>
              <div className="text-[10px] font-mono text-sentinel-dim">target@upi</div>
            </div>
          </div>

          <div className="p-2 rounded bg-sentinel-bg/60 border border-sentinel-border flex items-center gap-2">
            <Mail className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            <div>
              <div className="text-[11px] font-medium text-sentinel-text">Email IDs</div>
              <div className="text-[10px] font-mono text-sentinel-dim">mule@mail.com</div>
            </div>
          </div>

          <div className="p-2 rounded bg-sentinel-bg/60 border border-sentinel-border flex items-center gap-2">
            <FileText className="w-3.5 h-3.5 text-purple-400 shrink-0" />
            <div>
              <div className="text-[11px] font-medium text-sentinel-text">Case References</div>
              <div className="text-[10px] font-mono text-sentinel-dim">CASE-..., complaint:...</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
