import {
  EntityRiskResponse,
  FraudRingResponse,
  GraphNeighborsResponse,
  RelatedIncidentsResponse,
  SharedEntityResponse,
} from './graph';

export type InvestigationTargetType =
  | 'complaint'
  | 'phone'
  | 'email'
  | 'upi'
  | 'bank_account'
  | 'device'
  | 'ip'
  | 'person';

export interface InvestigationRequest {
  target_type: InvestigationTargetType;
  target_value: string;
}

export interface InvestigationEvidence {
  neighbors: GraphNeighborsResponse;
  related_incidents: RelatedIncidentsResponse;
  risk: EntityRiskResponse;
  fraud_ring: FraudRingResponse;
  shared_entities: SharedEntityResponse;
}

export interface InvestigationReport {
  summary: string;
  risk_level: string;
  confidence: number;
  findings: string[];
  key_entities: string[];
  recommended_actions: string[];
}

export interface InvestigationResponse {
  target_type: InvestigationTargetType;
  target_value: string;
  evidence: InvestigationEvidence;
  report: InvestigationReport;
}

export interface ReportTelemetry {
  correlation_id: string;
  provider: string;
  model: string;
  latency_ms: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  prompt_hash: string;
  template_version: string;
  summary_version: string;
  report_context_version: string;
  generated_at: string;
}

export interface ProfessionalInvestigationReport {
  report_id: string;
  target_value: string;
  generated_at: string;
  executive_summary: {
    summary_text: string;
    overall_risk_level: string;
    key_takeaways: string[];
  };
  investigation_scope: {
    target_value: string;
    target_type?: string | null;
    total_complaints: number;
    total_entities: number;
    duration_days: number;
  };
  timeline_summary: {
    timeline_narrative: string;
    milestones: Array<{
      event_type: string;
      timestamp: string;
      title: string;
      description: string;
    }>;
  };
  key_findings: Array<{
    finding_id: string;
    title: string;
    description: string;
    severity: string;
    confidence: number;
    citations: string[];
  }>;
  fraud_network_evolution: {
    evolution_narrative: string;
    network_stage: string;
  };
  evidence_assessment: {
    evidence_summary: string;
    supporting_evidence_count: number;
  };
  recommendations: Array<{
    recommendation_id: string;
    action: string;
    priority: string;
    rationale: string;
    trigger: string;
    target_entities: string[];
  }>;
  limitations: {
    data_quality_assessment: string;
    limitations: string[];
  };
  conclusion: {
    summary_conclusion: string;
  };
  telemetry: ReportTelemetry;
}
