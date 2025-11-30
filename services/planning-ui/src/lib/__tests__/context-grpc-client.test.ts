/**
 * Unit tests for Context gRPC client helpers
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import * as grpc from '@grpc/grpc-js';
import * as contextClientModule from '../context-grpc-client';

// Mock dependencies
vi.mock('@grpc/grpc-js');
vi.mock('@grpc/proto-loader');
vi.mock('fs', () => ({
  existsSync: vi.fn(),
}));
vi.mock('module', () => ({
  createRequire: vi.fn(),
}));

describe('Context gRPC Client', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset cached client
    vi.resetModules();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('isServiceError', () => {
    it('should return true for valid ServiceError object', () => {
      const error: grpc.ServiceError = {
        code: grpc.status.NOT_FOUND,
        message: 'Not found',
        details: 'Resource not found',
        name: 'ServiceError',
      };

      expect(contextClientModule.isServiceError(error)).toBe(true);
    });

    it('should return false for plain Error', () => {
      const error = new Error('Regular error');
      expect(contextClientModule.isServiceError(error)).toBe(false);
    });

    it('should return false for null', () => {
      expect(contextClientModule.isServiceError(null)).toBeFalsy();
    });

    it('should return false for undefined', () => {
      expect(contextClientModule.isServiceError(undefined)).toBeFalsy();
    });

    it('should return false for object without code', () => {
      const error = { message: 'Error', details: 'Details' };
      expect(contextClientModule.isServiceError(error)).toBe(false);
    });

    it('should return false for object without details', () => {
      const error = { code: 404, message: 'Error' };
      expect(contextClientModule.isServiceError(error)).toBe(false);
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

      expect(contextClientModule.grpcErrorToHttpStatus(error)).toBe(404);
    });

    it('should map INVALID_ARGUMENT to 400', () => {
      const error: grpc.ServiceError = {
        code: grpc.status.INVALID_ARGUMENT,
        message: 'Invalid',
        details: '',
        name: 'ServiceError',
      };

      expect(contextClientModule.grpcErrorToHttpStatus(error)).toBe(400);
    });

    it('should map UNAUTHENTICATED to 401', () => {
      const error: grpc.ServiceError = {
        code: grpc.status.UNAUTHENTICATED,
        message: 'Unauthenticated',
        details: '',
        name: 'ServiceError',
      };

      expect(contextClientModule.grpcErrorToHttpStatus(error)).toBe(401);
    });

    it('should map PERMISSION_DENIED to 403', () => {
      const error: grpc.ServiceError = {
        code: grpc.status.PERMISSION_DENIED,
        message: 'Permission denied',
        details: '',
        name: 'ServiceError',
      };

      expect(contextClientModule.grpcErrorToHttpStatus(error)).toBe(403);
    });

    it('should map INTERNAL to 500', () => {
      const error: grpc.ServiceError = {
        code: grpc.status.INTERNAL,
        message: 'Internal error',
        details: '',
        name: 'ServiceError',
      };

      expect(contextClientModule.grpcErrorToHttpStatus(error)).toBe(500);
    });

    it('should map UNAVAILABLE to 503', () => {
      const error: grpc.ServiceError = {
        code: grpc.status.UNAVAILABLE,
        message: 'Service unavailable',
        details: '',
        name: 'ServiceError',
      };

      expect(contextClientModule.grpcErrorToHttpStatus(error)).toBe(503);
    });

    it('should map default/unknown codes to 500', () => {
      const error: grpc.ServiceError = {
        code: grpc.status.UNKNOWN,
        message: 'Unknown error',
        details: '',
        name: 'ServiceError',
      };

      expect(contextClientModule.grpcErrorToHttpStatus(error)).toBe(500);
    });
  });

  describe('promisifyGrpcCall', () => {
    it('should resolve with response on success', async () => {
      const mockResponse = { success: true, data: 'test' };
      const mockCallFn = vi.fn((request, callback) => {
        callback(null, mockResponse);
        return {} as grpc.ClientUnaryCall;
      });

      const result = await contextClientModule.promisifyGrpcCall(mockCallFn, {});

      expect(result).toEqual(mockResponse);
      expect(mockCallFn).toHaveBeenCalled();
    });

    it('should reject with error on gRPC error', async () => {
      const error: grpc.ServiceError = {
        code: grpc.status.NOT_FOUND,
        message: 'Not found',
        details: '',
        name: 'ServiceError',
      };
      const mockCallFn = vi.fn((request, callback) => {
        callback(error, null);
        return {} as grpc.ClientUnaryCall;
      });

      await expect(contextClientModule.promisifyGrpcCall(mockCallFn, {})).rejects.toEqual(error);
      expect(mockCallFn).toHaveBeenCalled();
    });
  });
});

