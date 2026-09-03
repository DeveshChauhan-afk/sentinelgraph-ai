export interface GraphSummary {
  total_nodes: number;
  total_edges: number;
  complaints: number;
  phones: number;
  emails: number;
  upis: number;
  organizations: number;
  persons: number;
  locations: number;
  bank_accounts: number;
  average_degree: number;
}

export interface TopConnectedEntity {
  id: string;
  label: string;
  type: string;
  connection_count: number;
  complaint_count: number;
}

export interface SharedEntityAnalysis {
  entity_id: string;
  entity_label: string;
  entity_type: string;
  complaint_count: number;
  complaint_ids: string[];
}
