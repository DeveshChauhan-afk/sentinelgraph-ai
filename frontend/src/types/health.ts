export interface DependencyCheck {
  status: 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY';
  latency_ms: number;
  message?: string | null;
}

export interface HealthSummaryResponse {
  status: 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY';
  service: string;
  version: string;
  environment: string;
  dependencies: {
    postgres?: DependencyCheck;
    neo4j?: DependencyCheck;
    gemini?: DependencyCheck;
    [key: string]: DependencyCheck | undefined;
  };
}

export interface ReadinessResponse {
  status: 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY';
  is_ready: boolean;
  dependencies: Record<string, DependencyCheck>;
}
