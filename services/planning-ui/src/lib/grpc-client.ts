/**
 * gRPC client for Planning Service
 * Uses generated code from .proto files (generated during Docker build)
 * Falls back to proto-loader for development if generated code not available
 */

import * as grpc from '@grpc/grpc-js';
import * as protoLoader from '@grpc/proto-loader';
import { getPlanningServiceConfig } from './config';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { existsSync } from 'fs';
import { createRequire } from 'module';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const require = createRequire(import.meta.url);

/**
 * Planning Service client interface
 */
export interface PlanningServiceClient extends grpc.Client {
  createProject(
    request: any,
    callback: (error: grpc.ServiceError | null, response: any) => void
  ): grpc.ClientUnaryCall;

  getProject(
    request: any,
    callback: (error: grpc.ServiceError | null, response: any) => void
  ): grpc.ClientUnaryCall;

  listProjects(
    request: any,
    callback: (error: grpc.ServiceError | null, response: any) => void
  ): grpc.ClientUnaryCall;

  createEpic(
    request: any,
    callback: (error: grpc.ServiceError | null, response: any) => void
  ): grpc.ClientUnaryCall;

  getEpic(
    request: any,
    callback: (error: grpc.ServiceError | null, response: any) => void
  ): grpc.ClientUnaryCall;

  listEpics(
    request: any,
    callback: (error: grpc.ServiceError | null, response: any) => void
  ): grpc.ClientUnaryCall;

  createStory(
    request: any,
    callback: (error: grpc.ServiceError | null, response: any) => void
  ): grpc.ClientUnaryCall;

  getStory(
    request: any,
    callback: (error: grpc.ServiceError | null, response: any) => void
  ): grpc.ClientUnaryCall;

  listStories(
    request: any,
    callback: (error: grpc.ServiceError | null, response: any) => void
  ): grpc.ClientUnaryCall;

  transitionStory(
    request: any,
    callback: (error: grpc.ServiceError | null, response: any) => void
  ): grpc.ClientUnaryCall;

  approveDecision(
    request: any,
    callback: (error: grpc.ServiceError | null, response: any) => void
  ): grpc.ClientUnaryCall;

  rejectDecision(
    request: any,
    callback: (error: grpc.ServiceError | null, response: any) => void
  ): grpc.ClientUnaryCall;

  createTask(
    request: any,
    callback: (error: grpc.ServiceError | null, response: any) => void
  ): grpc.ClientUnaryCall;

  getTask(
    request: any,
    callback: (error: grpc.ServiceError | null, response: any) => void
  ): grpc.ClientUnaryCall;

  listTasks(
    request: any,
    callback: (error: grpc.ServiceError | null, response: any) => void
  ): grpc.ClientUnaryCall;
}

let cachedClient: PlanningServiceClient | null = null;

/**
 * Try to load generated gRPC code (preferred method)
 */
function tryLoadGeneratedCode(): any | null {
  const possiblePaths = [
    join(process.cwd(), 'gen/fleet/planning/v2/planning_grpc_pb.js'), // Production container
    join(__dirname, '../../../gen/fleet/planning/v2/planning_grpc_pb.js'), // Development
    join(__dirname, '../../../../gen/fleet/planning/v2/planning_grpc_pb.js'), // Production dist
    '/app/gen/fleet/planning/v2/planning_grpc_pb.js', // Container absolute
  ];

  for (const path of possiblePaths) {
    if (existsSync(path)) {
      try {
        // Use CommonJS require for generated code
        const generated = require(path);
        if (generated.PlanningServiceClient) {
          return generated.PlanningServiceClient;
        }
      } catch (e) {
        console.warn(`Failed to load generated code from ${path}:`, e);
      }
    }
  }

  return null;
}

/**
 * Load client using proto-loader (fallback for development)
 */
async function loadClientFromProto(): Promise<any> {
  const possiblePaths = [
    join(__dirname, '../../proto/fleet/planning/v2/planning.proto'), // Development
    join(__dirname, '../../../proto/fleet/planning/v2/planning.proto'), // Production dist
    join(process.cwd(), 'proto/fleet/planning/v2/planning.proto'), // Container absolute
    '/app/proto/fleet/planning/v2/planning.proto', // Container fallback
  ];

  let protoPath: string | null = null;
  for (const path of possiblePaths) {
    if (existsSync(path)) {
      protoPath = path;
      break;
    }
  }

  if (!protoPath) {
    throw new Error('Proto file not found. Ensure planning.proto is available.');
  }

  const packageDefinition = await protoLoader.load(protoPath, {
    keepCase: true,
    longs: String,
    enums: String,
    defaults: true,
    oneofs: true,
  });

  const planningProto = grpc.loadPackageDefinition(packageDefinition) as any;

  if (!planningProto.fleet?.planning?.v2?.PlanningService) {
    throw new Error('Failed to load PlanningService from protobuf definition.');
  }

  return planningProto.fleet.planning.v2.PlanningService;
}

/**
 * Get or create Planning Service gRPC client
 * Uses singleton pattern to reuse client instance
 * Prefers generated code, falls back to proto-loader
 */
export async function getPlanningClient(): Promise<PlanningServiceClient> {
  if (cachedClient) {
    return cachedClient;
  }

  const config = getPlanningServiceConfig();

  // Try to use generated code first (preferred)
  const GeneratedClient = tryLoadGeneratedCode();
  const PlanningService = GeneratedClient || await loadClientFromProto();

  // Create client with insecure credentials (for internal K8s cluster communication)
  const client = new PlanningService(
    `${config.grpcHost}:${config.grpcPort}`,
    grpc.credentials.createInsecure(),
    {
      'grpc.keepalive_time_ms': 30000,
      'grpc.keepalive_timeout_ms': 5000,
      'grpc.keepalive_permit_without_calls': true,
      'grpc.http2.max_pings_without_data': 0,
      'grpc.http2.min_time_between_pings_ms': 10000,
      'grpc.http2.min_ping_interval_without_data_ms': 300000,
    }
  ) as PlanningServiceClient;

  cachedClient = client;
  return client;
}

/**
 * Check if an error is a gRPC ServiceError
 */
export function isServiceError(error: unknown): error is grpc.ServiceError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'code' in error &&
    typeof (error as any).code === 'number' &&
    'message' in error &&
    typeof (error as any).message === 'string'
  );
}

/**
 * Convert gRPC error to HTTP status code
 */
export function grpcErrorToHttpStatus(error: grpc.ServiceError): number {
  switch (error.code) {
    case grpc.status.NOT_FOUND:
      return 404;
    case grpc.status.INVALID_ARGUMENT:
    case grpc.status.FAILED_PRECONDITION:
      return 400;
    case grpc.status.PERMISSION_DENIED:
      return 403;
    case grpc.status.UNAUTHENTICATED:
      return 401;
    case grpc.status.RESOURCE_EXHAUSTED:
      return 429;
    case grpc.status.UNAVAILABLE:
    case grpc.status.DEADLINE_EXCEEDED:
      return 503;
    case grpc.status.INTERNAL:
    case grpc.status.UNKNOWN:
    default:
      return 500;
  }
}

/**
 * Promisify a gRPC unary call
 */
export function promisifyGrpcCall<TRequest, TResponse>(
  clientMethod: (
    request: TRequest,
    callback: (error: grpc.ServiceError | null, response: TResponse) => void
  ) => grpc.ClientUnaryCall,
  request: TRequest
): Promise<TResponse> {
  return new Promise<TResponse>((resolve, reject) => {
    clientMethod(request, (error, response) => {
      if (error) {
        reject(error);
      } else if (!response) {
        reject(new Error('Empty response from gRPC call'));
      } else {
        resolve(normalizeGrpcMessage(response));
      }
    });
  });
}

/**
 * Normalize gRPC response messages (generated classes or plain objects) into
 * simple JSON-friendly objects with snake_case keys so the rest of the UI can
 * keep treating responses like they came from proto-loader.
 */
function normalizeGrpcMessage<T>(value: T): T {
  if (value === null || value === undefined) {
    return value;
  }

  if (Array.isArray(value)) {
    return value.map((item) => normalizeGrpcMessage(item)) as T;
  }

  if (typeof value === 'object') {
    const maybeMessage = value as { toObject?: () => unknown };
    if (typeof maybeMessage.toObject === 'function') {
      return normalizeGrpcMessage(maybeMessage.toObject()) as T;
    }

    const normalizedEntries: Record<string, unknown> = {};
    for (const [rawKey, rawVal] of Object.entries(value as Record<string, unknown>)) {
      if (rawKey.startsWith('$')) {
        continue; // Skip protobuf metadata fields like $jspbMessageInstance
      }

      const keyWithoutListSuffix = stripListSuffix(rawKey);
      const normalizedKey = camelToSnake(keyWithoutListSuffix);
      normalizedEntries[normalizedKey] = normalizeGrpcMessage(rawVal);
    }

    return normalizedEntries as T;
  }

  return value;
}

function stripListSuffix(key: string): string {
  if (!key.endsWith('List')) {
    return key;
  }

  const base = key.slice(0, -4);
  if (base.endsWith('s')) {
    return base;
  }

  return `${base}s`;
}

function camelToSnake(key: string): string {
  return key
    .replace(/([A-Z])/g, '_$1')
    .replace(/__+/g, '_')
    .toLowerCase();
}

