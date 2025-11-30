/**
 * gRPC client for Context Service
 * Uses generated code from .proto files (generated during Docker build)
 * Falls back to proto-loader for development if generated code not available
 */

import * as grpc from '@grpc/grpc-js';
import * as protoLoader from '@grpc/proto-loader';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { existsSync } from 'fs';
import { createRequire } from 'module';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const require = createRequire(import.meta.url);

/**
 * Context Service client interface
 */
export interface ContextServiceClient extends grpc.Client {
  getGraphRelationships(
    request: any,
    callback: (error: grpc.ServiceError | null, response: any) => void
  ): grpc.ClientUnaryCall;
}

let cachedClient: ContextServiceClient | null = null;

/**
 * Get Context Service configuration
 */
function getContextServiceConfig(): { host: string; port: number } {
  const urlOrHost = import.meta.env.PUBLIC_CONTEXT_SERVICE_URL || 'context-service.swe-ai-fleet.svc.cluster.local';
  let grpcHost = urlOrHost.replace(/^https?:\/\//, '');
  grpcHost = grpcHost.split(':')[0];
  const grpcPort = Number(import.meta.env.PUBLIC_CONTEXT_SERVICE_PORT || '50054');
  return { host: grpcHost, port: grpcPort };
}

/**
 * Try to load generated gRPC code (preferred method)
 */
function tryLoadGeneratedCode(): any | null {
  const possiblePaths = [
    join(process.cwd(), 'gen/fleet/context/v1/context_grpc_pb.js'),
    join(__dirname, '../../../gen/fleet/context/v1/context_grpc_pb.js'),
    join(__dirname, '../../../../gen/fleet/context/v1/context_grpc_pb.js'),
    '/app/gen/fleet/context/v1/context_grpc_pb.js',
  ];

  for (const path of possiblePaths) {
    if (existsSync(path)) {
      try {
        const grpcModule = require(path);
        const pbModule = require(path.replace('_grpc_pb.js', '_pb.js'));
        return { grpc: grpcModule, pb: pbModule };
      } catch (error) {
        console.warn(`Failed to load context gRPC code from ${path}:`, error);
      }
    }
  }

  return null;
}

/**
 * Load proto using proto-loader (fallback for development)
 */
function loadProtoWithLoader(): protoLoader.PackageDefinition {
  const protoPath = join(__dirname, '../../../specs/fleet/context/v1/context.proto');
  const altProtoPath = join(process.cwd(), 'specs/fleet/context/v1/context.proto');

  const actualPath = existsSync(protoPath) ? protoPath : altProtoPath;

  return protoLoader.loadSync(actualPath, {
    keepCase: true,
    longs: String,
    enums: String,
    defaults: true,
    oneofs: true,
  });
}

/**
 * Get or create Context Service client
 */
export function getContextClient(): ContextServiceClient {
  if (cachedClient) {
    return cachedClient;
  }

  const config = getContextServiceConfig();
  const generated = tryLoadGeneratedCode();

  if (generated) {
    // Use generated code
    const ContextService = generated.grpc.ContextService;
    cachedClient = new ContextService(
      `${config.host}:${config.port}`,
      grpc.credentials.createInsecure()
    ) as ContextServiceClient;
  } else {
    // Fallback to proto-loader
    const packageDef = loadProtoWithLoader();
    const contextProto = grpc.loadPackageDefinition(packageDef) as any;
    const ContextService = contextProto.fleet.context.v1.ContextService;
    cachedClient = new ContextService(
      `${config.host}:${config.port}`,
      grpc.credentials.createInsecure()
    ) as ContextServiceClient;
  }

  return cachedClient;
}

/**
 * Promisify gRPC call
 */
export function promisifyGrpcCall<T>(
  callFn: (request: any, callback: (error: grpc.ServiceError | null, response: T) => void) => grpc.ClientUnaryCall,
  request: any
): Promise<T> {
  return new Promise((resolve, reject) => {
    callFn(request, (error, response) => {
      if (error) {
        reject(error);
      } else {
        resolve(response);
      }
    });
  });
}

/**
 * Check if error is a gRPC service error
 */
export function isServiceError(error: any): error is grpc.ServiceError {
  return error && typeof error.code === 'number' && typeof error.details === 'string';
}

/**
 * Convert gRPC error code to HTTP status
 */
export function grpcErrorToHttpStatus(error: grpc.ServiceError): number {
  switch (error.code) {
    case grpc.status.NOT_FOUND:
      return 404;
    case grpc.status.INVALID_ARGUMENT:
      return 400;
    case grpc.status.UNAUTHENTICATED:
      return 401;
    case grpc.status.PERMISSION_DENIED:
      return 403;
    case grpc.status.INTERNAL:
      return 500;
    case grpc.status.UNAVAILABLE:
      return 503;
    default:
      return 500;
  }
}

