import React from 'react';
import { CheckCircle2 } from 'lucide-react';

export const EvaluationPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="p-4 rounded-lg bg-sentinel-surface border border-sentinel-border">
        <h2 className="text-base font-semibold text-sentinel-text">
          AI Evaluation & Guardrails
        </h2>
        <p className="text-xs text-sentinel-muted mt-0.5">
          Deterministic Citation Verification, Anti-Hallucination Audit & Golden Dataset Benchmarks.
        </p>
      </div>

      <div className="flex flex-col items-center justify-center p-12 text-center rounded-lg border border-dashed border-sentinel-border bg-sentinel-surface/30">
        <div className="w-12 h-12 rounded-full bg-emerald-950/40 border border-emerald-800/40 flex items-center justify-center mb-3 text-emerald-400">
          <CheckCircle2 className="w-6 h-6" />
        </div>
        <div className="text-sm font-semibold text-sentinel-text">
          Evaluation Dashboard Ready for Task 3
        </div>
        <div className="text-xs text-sentinel-muted max-w-md mt-1">
          In the upcoming phase, this screen will display real-time citation accuracy, anti-hallucination verification results, quality scores, and latency benchmarks.
        </div>
      </div>
    </div>
  );
};
