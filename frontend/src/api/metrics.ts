/**
 * SentinelGraph AI Prometheus Metrics Client
 * Safely parses LLM telemetry metrics from the backend Prometheus exposition.
 */

export interface LlmTelemetryMetrics {
  isAvailable: boolean;
  hasRecordedRequests: boolean;
  totalRequests: number;
  averageDurationMs: number | null;
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
  models: string[];
  lastScraped: Date;
}

/**
 * Safely extracts LLM telemetry from Prometheus exposition format.
 * Matches backend core metrics defined in backend/app/core/metrics.py:
 * - llm_requests_total
 * - llm_request_duration_seconds (count & sum)
 * - llm_tokens_total (type="prompt", type="completion")
 */
export function parseLlmTelemetryFromPrometheus(text: string): LlmTelemetryMetrics {
  const lines = text.split('\n');
  let hasLlmMetricSample = false;
  let totalRequests = 0;
  let hasRequestCount = false;
  let durationCount = 0;
  let durationSum = 0;
  let promptTokens = 0;
  let hasPromptTokens = false;
  let completionTokens = 0;
  let hasCompletionTokens = false;
  const models = new Set<string>();

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;

    // llm_requests_total
    const reqMatch = line.match(/^llm_requests_total(?:\{([^}]+)\})?\s+([0-9.eE+-]+)/);
    if (reqMatch) {
      hasLlmMetricSample = true;
      hasRequestCount = true;
      const val = parseFloat(reqMatch[2]);
      if (!isNaN(val)) totalRequests += val;
      const modelMatch = reqMatch[1]?.match(/model="([^"]+)"/);
      if (modelMatch) models.add(modelMatch[1]);
      continue;
    }

    // llm_request_duration_seconds_count
    const durCountMatch = line.match(
      /^llm_request_duration_seconds_count(?:\{([^}]+)\})?\s+([0-9.eE+-]+)/
    );
    if (durCountMatch) {
      hasLlmMetricSample = true;
      const val = parseFloat(durCountMatch[2]);
      if (!isNaN(val)) durationCount += val;
      const modelMatch = durCountMatch[1]?.match(/model="([^"]+)"/);
      if (modelMatch) models.add(modelMatch[1]);
      continue;
    }

    // llm_request_duration_seconds_sum
    const durSumMatch = line.match(
      /^llm_request_duration_seconds_sum(?:\{([^}]+)\})?\s+([0-9.eE+-]+)/
    );
    if (durSumMatch) {
      hasLlmMetricSample = true;
      const val = parseFloat(durSumMatch[2]);
      if (!isNaN(val)) durationSum += val;
      continue;
    }

    // llm_tokens_total
    const tokMatch = line.match(/^llm_tokens_total\{([^}]+)\}\s+([0-9.eE+-]+)/);
    if (tokMatch) {
      hasLlmMetricSample = true;
      const labels = tokMatch[1];
      const val = parseFloat(tokMatch[2]);
      if (!isNaN(val)) {
        if (labels.includes('type="prompt"')) {
          hasPromptTokens = true;
          promptTokens += val;
        } else if (labels.includes('type="completion"')) {
          hasCompletionTokens = true;
          completionTokens += val;
        }
      }
      const modelMatch = labels.match(/model="([^"]+)"/);
      if (modelMatch) models.add(modelMatch[1]);
      continue;
    }
  }

  const averageDurationMs =
    durationCount > 0 ? Math.round((durationSum / durationCount) * 1000 * 100) / 100 : null;

  return {
    isAvailable: true,
    hasRecordedRequests: hasLlmMetricSample && (totalRequests > 0 || hasRequestCount),
    totalRequests: hasRequestCount ? totalRequests : 0,
    averageDurationMs,
    promptTokens: hasPromptTokens ? promptTokens : 0,
    completionTokens: hasCompletionTokens ? completionTokens : 0,
    totalTokens:
      (hasPromptTokens ? promptTokens : 0) + (hasCompletionTokens ? completionTokens : 0),
    models: Array.from(models),
    lastScraped: new Date(),
  };
}

export const metricsApi = {
  /**
   * Scrapes GET /metrics and extracts available LLM telemetry safely.
   */
  getLlmTelemetry: async (): Promise<LlmTelemetryMetrics> => {
    const response = await fetch('/metrics', {
      headers: {
        Accept: 'text/plain, */*',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: Failed to scrape Prometheus metrics`);
    }

    const text = await response.text();
    return parseLlmTelemetryFromPrometheus(text);
  },
};
