export interface TimelineEvent {
  event_type: string;
  timestamp: string;
  title: string;
  description?: string | null;
  metadata?: Record<string, any>;
}

export interface EntityTimelineInfo {
  entity_type: string;
  entity_value: string;
  first_seen: string;
  first_seen_complaint: string;
  usage_count: number;
  complaint_ids: string[];
}

export interface TimelineStatistics {
  total_complaints: number;
  total_entities: number;
  phones: number;
  upis: number;
  emails: number;
  urls: number;
  bank_accounts: number;
  organizations: number;
  people: number;
  locations: number;
}

export interface TimelineInsight {
  title: string;
  description: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH';
}

export interface FraudEvolutionEvent {
  event_type: string;
  timestamp: string;
  title: string;
  description: string;
  related_entities: string[];
  related_complaints: string[];
  metadata?: Record<string, any>;
}

export interface TimelineResponse {
  investigation_target: string;
  total_events: number;
  start_time?: string | null;
  end_time?: string | null;
  events: TimelineEvent[];
  entity_first_seen: EntityTimelineInfo[];
  statistics?: TimelineStatistics | null;
  insights: TimelineInsight[];
  fraud_evolution: FraudEvolutionEvent[];
}
