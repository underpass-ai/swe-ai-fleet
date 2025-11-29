/**
 * Configuration for Planning UI
 * Reads environment variables for Planning Service connection
 */

export interface PlanningServiceConfig {
  grpcHost: string;
  grpcPort: number;
}

/**
 * Get Planning Service configuration from environment variables
 * For gRPC, we only need hostname (no protocol like http://)
 */
export function getPlanningServiceConfig(): PlanningServiceConfig {
  // Extract hostname from URL if provided, or use direct hostname
  const urlOrHost = import.meta.env.PUBLIC_PLANNING_SERVICE_URL || 'planning.swe-ai-fleet.svc.cluster.local';

  // Remove protocol if present (http:// or https://)
  let grpcHost = urlOrHost.replace(/^https?:\/\//, '');

  // Remove port if included in URL (gRPC uses separate port config)
  grpcHost = grpcHost.split(':')[0];

  const grpcPort = Number(import.meta.env.PUBLIC_PLANNING_SERVICE_PORT || '50054');

  return {
    grpcHost,
    grpcPort,
  };
}

/**
 * Check if we're in development mode
 */
export function isDevelopment(): boolean {
  return import.meta.env.DEV;
}


