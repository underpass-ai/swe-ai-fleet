/**
 * Unit tests for gRPC client helpers and client initialization
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import * as grpc from '@grpc/grpc-js';
import * as protoLoader from '@grpc/proto-loader';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import {
  isServiceError,
  grpcErrorToHttpStatus,
  promisifyGrpcCall,
  getPlanningClient,
} from '../grpc-client';
import * as configModule from '../config';

// Mock dependencies
vi.mock('../config');
vi.mock('@grpc/grpc-js');
vi.mock('@grpc/proto-loader');
vi.mock('fs', () => ({
  existsSync: vi.fn(),
}));
vi.mock('module', () => ({
  createRequire: vi.fn(),
}));

describe('grpc-client helpers', () => {
  describe('isServiceError', () => {
    it('should return true for valid ServiceError object', () => {
      const error: grpc.ServiceError = {
        code: grpc.status.NOT_FOUND,
        message: 'Not found',
        details: 'Resource not found',
        name: 'ServiceError',
      };

      expect(isServiceError(error)).toBe(true);
    });

    it('should return false for plain Error', () => {
      const error = new Error('Regular error');
      expect(isServiceError(error)).toBe(false);
    });

    it('should return false for null', () => {
      expect(isServiceError(null)).toBe(false);
    });

    it('should return false for undefined', () => {
      expect(isServiceError(undefined)).toBe(false);
    });

    it('should return false for object without code', () => {
      const error = { message: 'Error' };
      expect(isServiceError(error)).toBe(false);
    });

    it('should return false for object without message', () => {
      const error = { code: 404 };
      expect(isServiceError(error)).toBe(false);
    });

    it('should return false for object with non-numeric code', () => {
      const error = { code: '404', message: 'Error' };
      expect(isServiceError(error)).toBe(false);
    });
  });

  describe('grpcErrorToHttpStatus', () => {
    it('should map NOT_FOUND to 404', () => {
      const error: grpc.ServiceError = {
        code: grpc.status.NOT_FOUND,
        message: 'Not found',
        details: '',
        name: 'ServiceError',
      };

      expect(grpcErrorToHttpStatus(error)).toBe(404);
    });

    it('should map INVALID_ARGUMENT to 400', () => {
      const error: grpc.ServiceError = {
        code: grpc.status.INVALID_ARGUMENT,
        message: 'Invalid',
        details: '',
        name: 'ServiceError',
      };

      expect(grpcErrorToHttpStatus(error)).toBe(400);
    });

    it('should map FAILED_PRECONDITION to 400', () => {
      const error: grpc.ServiceError = {
        code: grpc.status.FAILED_PRECONDITION,
        message: 'Precondition failed',
        details: '',
        name: 'ServiceError',
      };

      expect(grpcErrorToHttpStatus(error)).toBe(400);
    });

    it('should map PERMISSION_DENIED to 403', () => {
      const error: grpc.ServiceError = {
        code: grpc.status.PERMISSION_DENIED,
        message: 'Permission denied',
        details: '',
        name: 'ServiceError',
      };

      expect(grpcErrorToHttpStatus(error)).toBe(403);
    });

    it('should map UNAUTHENTICATED to 401', () => {
      const error: grpc.ServiceError = {
        code: grpc.status.UNAUTHENTICATED,
        message: 'Unauthenticated',
        details: '',
        name: 'ServiceError',
      };

      expect(grpcErrorToHttpStatus(error)).toBe(401);
    });

    it('should map RESOURCE_EXHAUSTED to 429', () => {
      const error: grpc.ServiceError = {
        code: grpc.status.RESOURCE_EXHAUSTED,
        message: 'Resource exhausted',
        details: '',
        name: 'ServiceError',
      };

      expect(grpcErrorToHttpStatus(error)).toBe(429);
    });

    it('should map UNAVAILABLE to 503', () => {
      const error: grpc.ServiceError = {
        code: grpc.status.UNAVAILABLE,
        message: 'Unavailable',
        details: '',
        name: 'ServiceError',
      };

      expect(grpcErrorToHttpStatus(error)).toBe(503);
    });

    it('should map DEADLINE_EXCEEDED to 503', () => {
      const error: grpc.ServiceError = {
        code: grpc.status.DEADLINE_EXCEEDED,
        message: 'Deadline exceeded',
        details: '',
        name: 'ServiceError',
      };

      expect(grpcErrorToHttpStatus(error)).toBe(503);
    });

    it('should map INTERNAL to 500', () => {
      const error: grpc.ServiceError = {
        code: grpc.status.INTERNAL,
        message: 'Internal error',
        details: '',
        name: 'ServiceError',
      };

      expect(grpcErrorToHttpStatus(error)).toBe(500);
    });

    it('should map UNKNOWN to 500', () => {
      const error: grpc.ServiceError = {
        code: grpc.status.UNKNOWN,
        message: 'Unknown error',
        details: '',
        name: 'ServiceError',
      };

      expect(grpcErrorToHttpStatus(error)).toBe(500);
    });

    it('should map default/unknown codes to 500', () => {
      const error: grpc.ServiceError = {
        code: 999 as grpc.status,
        message: 'Unknown code',
        details: '',
        name: 'ServiceError',
      };

      expect(grpcErrorToHttpStatus(error)).toBe(500);
    });
  });

  describe('promisifyGrpcCall', () => {
    it('should resolve with response on success', async () => {
      const mockMethod = vi.fn((request: any, callback: any) => {
        callback(null, { data: 'success' });
        return {} as grpc.ClientUnaryCall;
      });

      const result = await promisifyGrpcCall(mockMethod, { id: '123' });

      expect(result).toEqual({ data: 'success' });
      expect(mockMethod).toHaveBeenCalledWith({ id: '123' }, expect.any(Function));
    });

    it('should reject with error on gRPC error', async () => {
      const error: grpc.ServiceError = {
        code: grpc.status.NOT_FOUND,
        message: 'Not found',
        details: '',
        name: 'ServiceError',
      };

      const mockMethod = vi.fn((request: any, callback: any) => {
        callback(error, null);
        return {} as grpc.ClientUnaryCall;
      });

      await expect(promisifyGrpcCall(mockMethod, { id: '123' })).rejects.toEqual(error);
    });

    it('should reject with error on empty response', async () => {
      const mockMethod = vi.fn((request: any, callback: any) => {
        callback(null, null);
        return {} as grpc.ClientUnaryCall;
      });

      await expect(promisifyGrpcCall(mockMethod, { id: '123' })).rejects.toThrow(
        'Empty response from gRPC call'
      );
    });

    it('should reject with error on undefined response', async () => {
      const mockMethod = vi.fn((request: any, callback: any) => {
        callback(null, undefined);
        return {} as grpc.ClientUnaryCall;
      });

      await expect(promisifyGrpcCall(mockMethod, { id: '123' })).rejects.toThrow(
        'Empty response from gRPC call'
      );
    });
  });

  describe('getPlanningClient', () => {
    const mockConfig = {
      grpcHost: 'planning.test.local',
      grpcPort: 50054,
    };

    beforeEach(() => {
      vi.mocked(configModule.getPlanningServiceConfig).mockReturnValue(mockConfig);
      // Clear module cache to reset cachedClient
      vi.resetModules();
    });

    afterEach(() => {
      vi.clearAllMocks();
    });

    it('should return cached client on subsequent calls', async () => {
      const fs = await import('fs');
      const protoLoader = await import('@grpc/proto-loader');
      const mockGrpc = await import('@grpc/grpc-js');

      // Mock proto file exists
      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        return path.includes('planning.proto');
      });

      const mockPackageDefinition = { test: 'definition' };
      vi.mocked(protoLoader.load).mockResolvedValue(mockPackageDefinition as any);

      // Create a mock constructor function that can be used with 'new'
      const mockClientInstance = {} as any;
      const mockPlanningService = vi.fn(function(this: any) {
        return mockClientInstance;
      }) as any;
      mockPlanningService.prototype = {};

      vi.mocked(mockGrpc.loadPackageDefinition).mockReturnValue({
        fleet: {
          planning: {
            v2: {
              PlanningService: mockPlanningService,
            },
          },
        },
      } as any);

      vi.mocked(mockGrpc.credentials.createInsecure).mockReturnValue({} as any);

      const { getPlanningClient } = await import('../grpc-client');

      const client1 = await getPlanningClient();
      const client2 = await getPlanningClient();

      expect(client1).toBe(client2);
      expect(mockPlanningService).toHaveBeenCalledTimes(1);
    });

    it('should use generated code when available', async () => {
      const fs = await import('fs');
      const module = await import('module');

      // Mock generated code exists
      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        return path.includes('planning_grpc_pb.js');
      });

      // Create a mock constructor function that can be used with 'new'
      const mockClientInstance = {} as any;
      const mockGeneratedClient = vi.fn(function(this: any) {
        return mockClientInstance;
      }) as any;
      mockGeneratedClient.prototype = {};

      const mockRequire = vi.fn(() => ({
        PlanningServiceClient: mockGeneratedClient,
      }));

      // Mock createRequire to return our mock require function
      vi.mocked(module.createRequire).mockImplementation(() => mockRequire as any);

      const mockGrpc = await import('@grpc/grpc-js');
      vi.mocked(mockGrpc.credentials.createInsecure).mockReturnValue({} as any);

      const { getPlanningClient } = await import('../grpc-client');
      const client = await getPlanningClient();

      expect(fs.existsSync).toHaveBeenCalled();
      expect(mockGeneratedClient).toHaveBeenCalledWith(
        `${mockConfig.grpcHost}:${mockConfig.grpcPort}`,
        expect.anything(),
        expect.objectContaining({
          'grpc.keepalive_time_ms': 30000,
        })
      );
      expect(client).toBeDefined();
    });

    it('should fallback to proto-loader when generated code not available', async () => {
      const fs = await import('fs');
      const protoLoader = await import('@grpc/proto-loader');

      // Mock generated code doesn't exist, but proto file does
      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        return path.includes('planning.proto') && !path.includes('planning_grpc_pb.js');
      });

      const mockPackageDefinition = { test: 'definition' };
      vi.mocked(protoLoader.load).mockResolvedValue(mockPackageDefinition as any);

      const mockGrpc = await import('@grpc/grpc-js');
      // Create a mock constructor function that can be used with 'new'
      const mockClientInstance = {} as any;
      const mockPlanningService = vi.fn(function(this: any) {
        return mockClientInstance;
      }) as any;
      mockPlanningService.prototype = {};

      vi.mocked(mockGrpc.loadPackageDefinition).mockReturnValue({
        fleet: {
          planning: {
            v2: {
              PlanningService: mockPlanningService,
            },
          },
        },
      } as any);

      vi.mocked(mockGrpc.credentials.createInsecure).mockReturnValue({} as any);

      const { getPlanningClient } = await import('../grpc-client');
      const client = await getPlanningClient();

      expect(protoLoader.load).toHaveBeenCalled();
      expect(mockPlanningService).toHaveBeenCalledWith(
        `${mockConfig.grpcHost}:${mockConfig.grpcPort}`,
        expect.anything(),
        expect.objectContaining({
          'grpc.keepalive_time_ms': 30000,
          'grpc.keepalive_timeout_ms': 5000,
          'grpc.keepalive_permit_without_calls': true,
          'grpc.http2.max_pings_without_data': 0,
          'grpc.http2.min_time_between_pings_ms': 10000,
          'grpc.http2.min_ping_interval_without_data_ms': 300000,
        })
      );
      expect(client).toBeDefined();
    });

    it('should handle error when generated code exists but require fails', async () => {
      const fs = await import('fs');
      const module = await import('module');

      // Mock generated code exists
      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        return path.includes('planning_grpc_pb.js');
      });

      // Mock require throws error
      const mockRequire = vi.fn(() => {
        throw new Error('Module not found');
      });
      vi.mocked(module.createRequire).mockImplementation(() => mockRequire as any);

      // Should fallback to proto-loader
      const protoLoader = await import('@grpc/proto-loader');
      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        return path.includes('planning.proto');
      });

      const mockPackageDefinition = { test: 'definition' };
      vi.mocked(protoLoader.load).mockResolvedValue(mockPackageDefinition as any);

      const mockGrpc = await import('@grpc/grpc-js');
      // Create a mock constructor function that can be used with 'new'
      const mockClientInstance = {} as any;
      const mockPlanningService = vi.fn(function(this: any) {
        return mockClientInstance;
      }) as any;
      mockPlanningService.prototype = {};

      vi.mocked(mockGrpc.loadPackageDefinition).mockReturnValue({
        fleet: {
          planning: {
            v2: {
              PlanningService: mockPlanningService,
            },
          },
        },
      } as any);

      vi.mocked(mockGrpc.credentials.createInsecure).mockReturnValue({} as any);

      const { getPlanningClient } = await import('../grpc-client');
      const client = await getPlanningClient();

      // Should fallback to proto-loader
      expect(protoLoader.load).toHaveBeenCalled();
      expect(client).toBeDefined();
    });

    it('should handle error when generated code exists but PlanningServiceClient missing', async () => {
      const fs = await import('fs');
      const module = await import('module');

      // Mock generated code exists
      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        return path.includes('planning_grpc_pb.js');
      });

      // Mock require returns object without PlanningServiceClient
      const mockRequire = vi.fn(() => ({}));
      vi.mocked(module.createRequire).mockImplementation(() => mockRequire as any);

      // Should fallback to proto-loader
      const protoLoader = await import('@grpc/proto-loader');
      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        return path.includes('planning.proto');
      });

      const mockPackageDefinition = { test: 'definition' };
      vi.mocked(protoLoader.load).mockResolvedValue(mockPackageDefinition as any);

      const mockGrpc = await import('@grpc/grpc-js');
      // Create a mock constructor function that can be used with 'new'
      const mockClientInstance = {} as any;
      const mockPlanningService = vi.fn(function(this: any) {
        return mockClientInstance;
      }) as any;
      mockPlanningService.prototype = {};

      vi.mocked(mockGrpc.loadPackageDefinition).mockReturnValue({
        fleet: {
          planning: {
            v2: {
              PlanningService: mockPlanningService,
            },
          },
        },
      } as any);

      vi.mocked(mockGrpc.credentials.createInsecure).mockReturnValue({} as any);

      const { getPlanningClient } = await import('../grpc-client');
      const client = await getPlanningClient();

      // Should fallback to proto-loader
      expect(protoLoader.load).toHaveBeenCalled();
      expect(client).toBeDefined();
    });

    it('should throw error when proto file not found', async () => {
      const fs = await import('fs');

      // Mock neither generated code nor proto file exist
      vi.mocked(fs.existsSync).mockReturnValue(false);

      const { getPlanningClient } = await import('../grpc-client');

      await expect(getPlanningClient()).rejects.toThrow('Proto file not found');
    });

    it('should throw error when PlanningService not in proto definition', async () => {
      const fs = await import('fs');
      const protoLoader = await import('@grpc/proto-loader');

      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        return path.includes('planning.proto');
      });

      const mockPackageDefinition = { test: 'definition' };
      vi.mocked(protoLoader.load).mockResolvedValue(mockPackageDefinition as any);

      const mockGrpc = await import('@grpc/grpc-js');
      vi.mocked(mockGrpc.loadPackageDefinition).mockReturnValue({
        fleet: {
          planning: {
            v2: {}, // No PlanningService
          },
        },
      } as any);

      const { getPlanningClient } = await import('../grpc-client');

      await expect(getPlanningClient()).rejects.toThrow(
        'Failed to load PlanningService from protobuf definition'
      );
    });

    it('should try multiple paths for generated code', async () => {
      const fs = await import('fs');
      const module = await import('module');

      // Mock first path doesn't exist, second path exists
      let callCount = 0;
      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        if (path.includes('planning_grpc_pb.js')) {
          callCount++;
          // Return true on second call (second path) - stops checking after finding it
          return callCount >= 2;
        }
        return false;
      });

      // Create a mock constructor function that can be used with 'new'
      const mockClientInstance = {} as any;
      const mockGeneratedClient = vi.fn(function(this: any) {
        return mockClientInstance;
      }) as any;
      mockGeneratedClient.prototype = {};

      const mockRequire = vi.fn(() => ({
        PlanningServiceClient: mockGeneratedClient,
      }));

      vi.mocked(module.createRequire).mockImplementation(() => mockRequire as any);

      const mockGrpc = await import('@grpc/grpc-js');
      vi.mocked(mockGrpc.credentials.createInsecure).mockReturnValue({} as any);

      const { getPlanningClient } = await import('../grpc-client');
      const client = await getPlanningClient();

      // Should stop checking after finding the file (second path)
      expect(fs.existsSync).toHaveBeenCalled();
      expect(mockGeneratedClient).toHaveBeenCalled();
      expect(client).toBeDefined();
    });

    it('should try multiple paths for proto file', async () => {
      const fs = await import('fs');
      const protoLoader = await import('@grpc/proto-loader');

      // Mock first paths don't exist, last path exists
      let callCount = 0;
      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        if (path.includes('planning.proto')) {
          callCount++;
          // Return true on last call (last path)
          return callCount >= 4;
        }
        return false;
      });

      const mockPackageDefinition = { test: 'definition' };
      vi.mocked(protoLoader.load).mockResolvedValue(mockPackageDefinition as any);

      const mockGrpc = await import('@grpc/grpc-js');
      // Create a mock constructor function that can be used with 'new'
      const mockClientInstance = {} as any;
      const mockPlanningService = vi.fn(function(this: any) {
        return mockClientInstance;
      }) as any;
      mockPlanningService.prototype = {};

      vi.mocked(mockGrpc.loadPackageDefinition).mockReturnValue({
        fleet: {
          planning: {
            v2: {
              PlanningService: mockPlanningService,
            },
          },
        },
      } as any);

      vi.mocked(mockGrpc.credentials.createInsecure).mockReturnValue({} as any);

      const { getPlanningClient } = await import('../grpc-client');
      const client = await getPlanningClient();

      expect(fs.existsSync).toHaveBeenCalled();
      expect(protoLoader.load).toHaveBeenCalled();
      expect(client).toBeDefined();
    });
  });
});
