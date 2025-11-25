/**
 * Configuration for Planning UI
 * Reads environment variables for Planning Service connection
 */

export interface PlanningServiceConfig {
  grpcUrl: string;
  grpcPort: number;
}

/**
 * Get Planning Service configuration from environment variables
 */
export function getPlanningServiceConfig(): PlanningServiceConfig {
  // In browser, we'll need to use a gRPC-Web proxy or REST API
  // For now, we'll use environment variables that can be set at build time
  const grpcUrl = import.meta.env.PUBLIC_PLANNING_SERVICE_URL || 'http://localhost:50051';
  const grpcPort = Number(import.meta.env.PUBLIC_PLANNING_SERVICE_PORT || '50051');

  return {
    grpcUrl,
    grpcPort,
  };
}

/**
 * Check if we're in development mode
 */
export function isDevelopment(): boolean {
  return import.meta.env.DEV;
}


