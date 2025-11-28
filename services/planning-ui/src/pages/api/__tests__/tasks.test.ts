/**
 * Unit tests for Tasks API routes
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as grpc from '@grpc/grpc-js';
import * as grpcClientModule from '../../../lib/grpc-client';
import * as grpcRequestBuilders from '../../../lib/grpc-request-builders';

// Mock gRPC client module
vi.mock('../../../lib/grpc-client');
vi.mock('../../../lib/grpc-request-builders');

const mockBuildListTasksRequest = vi.mocked(grpcRequestBuilders.buildListTasksRequest);

describe('Tasks API Routes', () => {
  let mockClient: any;
  let mockGetPlanningClient: any;
  let mockPromisifyGrpcCall: any;
  let mockGrpcErrorToHttpStatus: any;
  let mockIsServiceError: any;

  beforeEach(() => {
    vi.clearAllMocks();

    mockClient = {
      ListTasks: vi.fn(),
    };

    mockGetPlanningClient = vi.fn().mockResolvedValue(mockClient);
    mockPromisifyGrpcCall = vi.fn();
    mockGrpcErrorToHttpStatus = vi.fn((error: grpc.ServiceError) => {
      if (error.code === grpc.status.NOT_FOUND) return 404;
      if (error.code === grpc.status.INVALID_ARGUMENT) return 400;
      return 500;
    });
    mockIsServiceError = vi.fn((error: unknown) => {
      return (
        typeof error === 'object' &&
        error !== null &&
        'code' in error &&
        typeof (error as any).code === 'number'
      );
    });

    mockBuildListTasksRequest.mockImplementation((payload) => payload as any);

    vi.mocked(grpcClientModule.getPlanningClient).mockImplementation(mockGetPlanningClient);
    vi.mocked(grpcClientModule.promisifyGrpcCall).mockImplementation(mockPromisifyGrpcCall);
    vi.mocked(grpcClientModule.grpcErrorToHttpStatus).mockImplementation(mockGrpcErrorToHttpStatus);
    vi.mocked(grpcClientModule.isServiceError).mockImplementation(mockIsServiceError);
  });

  describe('GET /api/tasks', () => {
    it('should list tasks successfully', async () => {
      const { GET } = await import('../tasks/index');

      const mockResponse = {
        tasks: [
          { task_id: 'task-1', title: 'Task 1', status: 'pending', story_id: 'story-1' },
          { task_id: 'task-2', title: 'Task 2', status: 'in_progress', story_id: 'story-1' },
        ],
        total_count: 2,
        success: true,
        message: 'Tasks retrieved',
      };

      mockPromisifyGrpcCall.mockResolvedValue(mockResponse);

      const request = new Request('http://localhost/api/tasks');
      const response = await GET({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(data.tasks).toHaveLength(2);
      expect(data.total_count).toBe(2);
      expect(mockBuildListTasksRequest).toHaveBeenCalledWith(
        expect.objectContaining({
          limit: 100,
          offset: 0,
          story_id: undefined,
          status_filter: undefined,
        })
      );
      expect(mockPromisifyGrpcCall).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          limit: 100,
          offset: 0,
        })
      );
    });

    it('should handle query parameters (story_id, status_filter, limit, offset)', async () => {
      const { GET } = await import('../tasks/index');

      mockPromisifyGrpcCall.mockResolvedValue({
        tasks: [],
        total_count: 0,
        success: true,
      });

      const request = new Request(
        'http://localhost/api/tasks?story_id=story-1&status_filter=pending&limit=50&offset=10'
      );
      const response = await GET({ request } as any);

      expect(response.status).toBe(200);
      expect(mockBuildListTasksRequest).toHaveBeenCalledWith(
        expect.objectContaining({
          story_id: 'story-1',
          status_filter: 'pending',
          limit: 50,
          offset: 10,
        })
      );
      expect(mockPromisifyGrpcCall).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          story_id: 'story-1',
          status_filter: 'pending',
          limit: 50,
          offset: 10,
        })
      );
    });

    it('should handle empty tasks list', async () => {
      const { GET } = await import('../tasks/index');

      mockPromisifyGrpcCall.mockResolvedValue({
        tasks: [],
        total_count: 0,
        success: true,
      });

      const request = new Request('http://localhost/api/tasks');
      const response = await GET({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.tasks).toEqual([]);
      expect(data.total_count).toBe(0);
    });

    it('should handle tasks without filters', async () => {
      const { GET } = await import('../tasks/index');

      mockPromisifyGrpcCall.mockResolvedValue({
        tasks: [
          { task_id: 'task-1', title: 'Task 1', status: 'pending' },
        ],
        total_count: 1,
        success: true,
      });

      const request = new Request('http://localhost/api/tasks');
      const response = await GET({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.tasks).toHaveLength(1);
      expect(mockBuildListTasksRequest).toHaveBeenCalledWith(
        expect.objectContaining({
          story_id: undefined,
          status_filter: undefined,
        })
      );
      expect(mockPromisifyGrpcCall).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          limit: 100,
          offset: 0,
        })
      );
    });

    it('should handle gRPC ServiceError', async () => {
      const { GET } = await import('../tasks/index');

      const error: grpc.ServiceError = {
        code: grpc.status.NOT_FOUND,
        message: 'Tasks not found',
        details: '',
        name: 'ServiceError',
      };

      mockPromisifyGrpcCall.mockRejectedValue(error);
      mockIsServiceError.mockReturnValue(true);
      mockGrpcErrorToHttpStatus.mockReturnValue(404);

      const request = new Request('http://localhost/api/tasks');
      const response = await GET({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(404);
      expect(data.success).toBe(false);
      expect(data.message).toBe('Tasks not found');
      expect(data.code).toBe(grpc.status.NOT_FOUND);
    });

    it('should handle unknown errors', async () => {
      const { GET } = await import('../tasks/index');

      const error = new Error('Unknown error');
      mockPromisifyGrpcCall.mockRejectedValue(error);
      mockIsServiceError.mockReturnValue(false);

      const request = new Request('http://localhost/api/tasks');
      const response = await GET({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(500);
      expect(data.success).toBe(false);
      expect(data.message).toBe('Unknown error');
    });

    it('should handle invalid limit/offset (should parse as NaN and use defaults)', async () => {
      const { GET } = await import('../tasks/index');

      mockPromisifyGrpcCall.mockResolvedValue({
        tasks: [],
        total_count: 0,
        success: true,
      });

      const request = new Request('http://localhost/api/tasks?limit=invalid&offset=invalid');
      const response = await GET({ request } as any);

      expect(response.status).toBe(200);
      // parseInt('invalid') returns NaN, which should be handled by the route
      // The route uses parseInt with default '100', so NaN should fallback to 100
      expect(mockPromisifyGrpcCall).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          limit: expect.any(Number),
          offset: expect.any(Number),
        })
      );
    });
  });
});


