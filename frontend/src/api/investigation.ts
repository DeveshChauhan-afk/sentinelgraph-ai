import { apiFetch } from './client';
import {
  InvestigationRequest,
  InvestigationResponse,
  ProfessionalInvestigationReport,
  TimelineResponse,
} from '../types';

export const investigationApi = {
  /**
   * POST /api/v1/investigation/
   * Fast Graph-RAG AI investigation report.
   */
  investigate: (request: InvestigationRequest): Promise<InvestigationResponse> => {
    return apiFetch<InvestigationResponse>('/api/v1/investigation/', {
      method: 'POST',
      body: JSON.stringify(request),
      timeoutMs: 60000,
    });
  },

  /**
   * POST /api/v1/investigation/report
   * Deep structured professional investigation report with telemetry & citations.
   */
  generateReport: (
    request: InvestigationRequest
  ): Promise<ProfessionalInvestigationReport> => {
    return apiFetch<ProfessionalInvestigationReport>('/api/v1/investigation/report', {
      method: 'POST',
      body: JSON.stringify(request),
      timeoutMs: 90000,
    });
  },

  /**
   * GET /api/v1/timeline/{entity_value}
   * Chronological timeline reconstruction of connected fraud events.
   */
  getTimeline: (entityValue: string): Promise<TimelineResponse> => {
    return apiFetch<TimelineResponse>(
      `/api/v1/timeline/${encodeURIComponent(entityValue)}`
    );
  },
};
