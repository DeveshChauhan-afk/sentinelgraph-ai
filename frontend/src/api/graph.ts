import { apiFetch } from './client';
import {
  EntityRiskResponse,
  FraudRingResponse,
  GraphNeighborsResponse,
  GraphNode,
  GraphResponse,
  NetworkSummaryResponse,
  PathResponse,
  RelatedIncidentsResponse,
  SharedEntityResponse,
  TopRiskEntityResponse,
} from '../types';

export const graphApi = {
  /**
   * GET /api/v1/graph/entity/{value}
   */
  getEntity: (value: string): Promise<GraphNode> => {
    return apiFetch<GraphNode>(`/api/v1/graph/entity/${encodeURIComponent(value)}`);
  },

  /**
   * GET /api/v1/graph/entity/{value}/neighbors
   */
  getNeighbors: (value: string): Promise<GraphNeighborsResponse> => {
    return apiFetch<GraphNeighborsResponse>(
      `/api/v1/graph/entity/${encodeURIComponent(value)}/neighbors`
    );
  },

  /**
   * GET /api/v1/graph/entity/{value}/incidents
   */
  getRelatedIncidents: (value: string): Promise<RelatedIncidentsResponse> => {
    return apiFetch<RelatedIncidentsResponse>(
      `/api/v1/graph/entity/${encodeURIComponent(value)}/incidents`
    );
  },

  /**
   * GET /api/v1/graph/entity/{value}/risk
   */
  getEntityRisk: (value: string): Promise<EntityRiskResponse> => {
    return apiFetch<EntityRiskResponse>(
      `/api/v1/graph/entity/${encodeURIComponent(value)}/risk`
    );
  },

  /**
   * GET /api/v1/graph/entity/{value}/ring
   */
  getFraudRing: (value: string): Promise<FraudRingResponse> => {
    return apiFetch<FraudRingResponse>(
      `/api/v1/graph/entity/${encodeURIComponent(value)}/ring`
    );
  },

  /**
   * GET /api/v1/graph/network/summary
   */
  getNetworkSummary: (): Promise<NetworkSummaryResponse> => {
    return apiFetch<NetworkSummaryResponse>('/api/v1/graph/network/summary');
  },

  /**
   * GET /api/v1/graph/network/top-risk?limit=10
   */
  getTopRiskEntities: (limit = 10): Promise<TopRiskEntityResponse[]> => {
    return apiFetch<TopRiskEntityResponse[]>(
      `/api/v1/graph/network/top-risk?limit=${limit}`
    );
  },

  /**
   * GET /api/v1/graph/path?source=&target=
   */
  getShortestPath: (source: string, target: string): Promise<PathResponse> => {
    return apiFetch<PathResponse>(
      `/api/v1/graph/path?source=${encodeURIComponent(source)}&target=${encodeURIComponent(target)}`
    );
  },

  /**
   * GET /api/v1/graph/entity/{value}/shared
   */
  getSharedEntity: (value: string): Promise<SharedEntityResponse> => {
    return apiFetch<SharedEntityResponse>(
      `/api/v1/graph/entity/${encodeURIComponent(value)}/shared`
    );
  },

  /**
   * GET /api/v1/graph/visualization/{node_id}?depth=2
   */
  getVisualization: (nodeId: string, depth = 2): Promise<GraphResponse> => {
    return apiFetch<GraphResponse>(
      `/api/v1/graph/visualization/${encodeURIComponent(nodeId)}?depth=${depth}`
    );
  },
};
