export type ReporterType = 'citizen' | 'law_enforcement' | 'financial_institution' | 'other';
export type IncidentSource = 'web_portal' | 'helpline_1930' | 'bank_integration' | 'law_enforcement_api' | 'other';
export type IncidentStatus = 'new' | 'under_investigation' | 'escalated' | 'resolved' | 'closed';
export type Priority = 'low' | 'medium' | 'high' | 'critical';
export type ScamCategory =
  | 'upi_fraud'
  | 'phishing'
  | 'investment_scam'
  | 'identity_theft'
  | 'tech_support_scam'
  | 'job_scam'
  | 'loan_scam'
  | 'other';

export interface IncidentCreate {
  title: string;
  description: string;
  reporter_type: ReporterType;
  source: IncidentSource;
  case_reference?: string | null;
}

export interface IncidentResponse {
  id: string;
  title: string;
  description: string;
  reporter_type: ReporterType;
  source: IncidentSource;
  case_reference?: string | null;
  status: IncidentStatus;
  priority: Priority;
  scam_category?: ScamCategory | null;
  ai_summary?: string | null;
  risk_score?: number | null;
  graph_node_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface IncidentListResponse {
  id: string;
  title: string;
  status: IncidentStatus;
  priority: Priority;
  created_at: string;
  reporter_type: ReporterType;
  risk_score?: number | null;
  graph_node_id?: string | null;
  case_reference?: string | null;
}
