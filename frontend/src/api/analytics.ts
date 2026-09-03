import { apiFetch } from './client';
import { GraphSummary, SharedEntityAnalysis, TopConnectedEntity } from '../types';

export const analyticsApi = {
  /**
   * GET /api/v1/analytics/summary
   * High-level network statistics and node/edge breakdowns.
   */
  getSummary: (): Promise<GraphSummary> => {
    return apiFetch<GraphSummary>('/api/v1/analytics/summary');
  },

  /**
   * GET /api/v1/analytics/top-connected?limit=10
   * Top connected entities ranked by relationship degree.
   */
  getTopConnected: (limit = 10): Promise<TopConnectedEntity[]> => {
    return apiFetch<TopConnectedEntity[]>(`/api/v1/analytics/top-connected?limit=${limit}`);
  },

  /**
   * GET /api/v1/analytics/shared-entities?minimum_complaints=2
   * Entities shared across multiple complaints.
   */
  getSharedEntities: (minimumComplaints = 2): Promise<SharedEntityAnalysis[]> => {
    return apiFetch<SharedEntityAnalysis[]>(
      `/api/v1/analytics/shared-entities?minimum_complaints=${minimumComplaints}`
    );
  },
};
