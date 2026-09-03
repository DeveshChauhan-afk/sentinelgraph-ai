export type GraphLabel =
  | 'Complaint'
  | 'Phone'
  | 'UPI'
  | 'Email'
  | 'URL'
  | 'BankAccount'
  | 'Organization'
  | 'Person'
  | 'Location';

export interface GraphNode {
  id: string;
  label: GraphLabel | string;
  properties: Record<string, any>;
}

export interface GraphRelationship {
  source: string;
  target: string;
  type: string;
  properties: Record<string, any>;
}

export interface GraphNeighborsResponse {
  entity: GraphNode;
  neighbors: GraphNode[];
}

export interface RelatedIncidentsResponse {
  entity: GraphNode;
  incidents: GraphNode[];
}

export interface RiskMetrics {
  incident_count: number;
  neighbor_count: number;
  phone_count: number;
  upi_count: number;
  email_count: number;
  organization_count: number;
}

export interface EntityRiskResponse {
  entity: GraphNode;
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  metrics: RiskMetrics;
  reasons: string[];
}

export interface FraudRingResponse {
  entity: GraphNode;
  nodes: GraphNode[];
  incidents: GraphNode[];
  total_nodes: number;
  total_incidents: number;
}

export interface NetworkSummaryResponse {
  total_nodes: number;
  total_relationships: number;
  complaints: number;
  phones: number;
  upis: number;
  emails: number;
  organizations: number;
}

export interface TopRiskEntityResponse {
  entity: GraphNode;
  incident_count: number;
  neighbor_count: number;
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
}

export interface PathResponse {
  found: boolean;
  length: number;
  nodes: GraphNode[];
}

export interface SharedEntityResponse {
  entity: GraphNode;
  complaints: GraphNode[];
  complaint_count: number;
}

/* Visualization Schemas (Cytoscape / Canvas) */
export interface VisualNode {
  id: string;
  label: string;
  type: string;
  properties: Record<string, any>;
}

export interface VisualEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  properties: Record<string, any>;
}

export interface VisualMetadata {
  node_count: number;
  edge_count: number;
  depth: number;
  generated_at: string;
}

export interface GraphResponse {
  nodes: VisualNode[];
  edges: VisualEdge[];
  metadata: VisualMetadata;
}
