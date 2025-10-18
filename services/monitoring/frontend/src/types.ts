export interface Event {
  source: 'NATS' | 'Ray' | 'Neo4j' | 'ValKey' | 'vLLM' | 'K8s';
  type: string;
  subject?: string;
  timestamp: string;
  data: Record<string, unknown>;
  metadata?: {
    sequence?: number;
    stream?: string;
  };
}

export interface Council {
  role: string;
  agents: Agent[];
  status: 'ready' | 'busy' | 'error';
  model: string;
}

export interface Agent {
  id: string;
  role: string;
  status: 'idle' | 'deliberating' | 'completed' | 'failed';
  task_id?: string;
  timestamp?: string;
}

export interface RayJob {
  job_id: string;
  task_id: string;
  agent_id: string;
  worker?: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  error?: string;
}

export interface SystemStatus {
  service: string;
  version: string;
  status: 'running' | 'error' | 'starting';
  replicas: number;
  uptime?: string;
}

