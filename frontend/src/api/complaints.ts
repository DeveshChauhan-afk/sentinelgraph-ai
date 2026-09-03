import { apiFetch } from './client';
import { IncidentCreate, IncidentListResponse, IncidentResponse } from '../types';

export const complaintsApi = {
  /**
   * GET /api/v1/complaints/?skip=0&limit=25
   * Paginated list of complaints.
   */
  listComplaints: (skip = 0, limit = 25): Promise<IncidentListResponse[]> => {
    return apiFetch<IncidentListResponse[]>(`/api/v1/complaints/?skip=${skip}&limit=${limit}`);
  },

  /**
   * GET /api/v1/complaints/{incident_id}
   * Get single complaint by ID.
   */
  getComplaint: (incidentId: string): Promise<IncidentResponse> => {
    return apiFetch<IncidentResponse>(`/api/v1/complaints/${incidentId}`);
  },

  /**
   * POST /api/v1/complaints/
   * Register new complaint, triggers entity extraction & graph construction.
   */
  createComplaint: (data: IncidentCreate): Promise<IncidentResponse> => {
    return apiFetch<IncidentResponse>('/api/v1/complaints/', {
      method: 'POST',
      body: JSON.stringify(data),
      timeoutMs: 60000, // Gemini extraction can take several seconds
    });
  },
};
