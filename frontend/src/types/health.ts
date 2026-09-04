export type HealthStatusType =
  | 'HEALTHY'
  | 'DEGRADED'
  | 'UNHEALTHY'
  | 'healthy'
  | 'degraded'
  | 'unhealthy';

export interface DependencyCheck {
  name?: string;
  status: HealthStatusType;
  latency_ms: number;
  critical?: boolean;
  message?: string | null;
}

export interface HealthSummaryResponse {
  status: HealthStatusType;
  service: string;
  version: string;
  environment: string;
  timestamp?: string;
  dependencies: {
    postgres?: DependencyCheck;
    neo4j?: DependencyCheck;
    gemini?: DependencyCheck;
    [key: string]: DependencyCheck | undefined;
  };
}

export interface ReadinessResponse {
  status: HealthStatusType;
  is_ready: boolean;
  timestamp?: string;
  dependencies: Record<string, DependencyCheck>;
}

