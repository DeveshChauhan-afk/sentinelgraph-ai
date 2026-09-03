import { apiFetch } from './client';
import { HealthSummaryResponse, ReadinessResponse } from '../types';

export const healthApi = {
  /**
   * GET /health
   * Overall operational health and backend dependencies (Postgres, Neo4j, Gemini).
   */
  getHealth: (): Promise<HealthSummaryResponse> => {
    return apiFetch<HealthSummaryResponse>('/health');
  },

  /**
   * GET /health/ready
   */
  getReadiness: (): Promise<ReadinessResponse> => {
    return apiFetch<ReadinessResponse>('/health/ready');
  },

  /**
   * GET /api/v1/version/
   */
  getVersion: (): Promise<{ version: string }> => {
    return apiFetch<{ version: string }>('/api/v1/version/');
  },
};
