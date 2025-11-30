/**
 * Unit tests for GET /api/tasks/[id] endpoint
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as grpc from '@grpc/grpc-js';
import * as grpcClientModule from '../../../lib/grpc-client';
import * as grpcRequestBuilders from '../../../lib/grpc-request-builders';

// Mock gRPC client module
vi.mock('../../../lib/grpc-client');
vi.mock('../../../lib/grpc-request-builders');

const mockBuildGetTaskRequest = vi.mocked(grpcRequestBuilders.buildGetTaskRequest);

describe('GET /api/tasks/[id]', () => {
  let mockClient: any;
  let mockGetPlanningClient: any;
  let mockPromisifyGrpcCall: any;
  let mockGrpcErrorToHttpStatus: any;
  let mockIsServiceError: any;

  beforeEach(() => {
    vi.clearAllMocks();

    mockClient = {
      getTask: vi.fn(),
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

    mockBuildGetTaskRequest.mockImplementation((payload) => payload as any);

    vi.mocked(grpcClientModule.getPlanningClient).mockImplementation(mockGetPlanningClient);
    vi.mocked(grpcClientModule.promisifyGrpcCall).mockImplementation(mockPromisifyGrpcCall);
    vi.mocked(grpcClientModule.grpcErrorToHttpStatus).mockImplementation(mockGrpcErrorToHttpStatus);
    vi.mocked(grpcClientModule.isServiceError).mockImplementation(mockIsServiceError);
  });

  it('should get task by id successfully', async () => {
    const { GET } = await import('../tasks/[id]');

    const mockResponse = {
      task: {
        task_id: 'task-123',
        title: 'Test Task',
        description: 'Description',
        story_id: 'story-1',
        status: 'pending',
      },
      success: true,
      message: 'Task retrieved successfully',
    };

    mockPromisifyGrpcCall.mockResolvedValue(mockResponse);

    const response = await GET({ params: { id: 'task-123' } } as any);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.success).toBe(true);
    expect(data.task.task_id).toBe('task-123');
    expect(data.task.title).toBe('Test Task');
    expect(mockBuildGetTaskRequest).toHaveBeenCalledWith({ task_id: 'task-123' });
    expect(mockPromisifyGrpcCall).toHaveBeenCalledWith(
      expect.any(Function),
      expect.objectContaining({ task_id: 'task-123' })
    );
  });

  it('should return 400 when id is missing', async () => {
    const { GET } = await import('../tasks/[id]');

    const response = await GET({ params: {} } as any);
    const data = await response.json();

    expect(response.status).toBe(400);
    expect(data.success).toBe(false);
    expect(data.message).toBe('task_id is required');
  });

  it('should return 400 when id is undefined', async () => {
    const { GET } = await import('../tasks/[id]');

    const response = await GET({ params: { id: undefined } } as any);
    const data = await response.json();

    expect(response.status).toBe(400);
    expect(data.success).toBe(false);
    expect(data.message).toBe('task_id is required');
  });

  it('should return 404 when task not found (success=false)', async () => {
    const { GET } = await import('../tasks/[id]');

    mockPromisifyGrpcCall.mockResolvedValue({
      success: false,
      message: 'Task not found',
    });

    const response = await GET({ params: { id: 'task-123' } } as any);
    const data = await response.json();

    expect(response.status).toBe(404);
    expect(data.success).toBe(false);
    expect(data.message).toBe('Task not found');
  });

  it('should return 404 when task is null', async () => {
    const { GET } = await import('../tasks/[id]');

    mockPromisifyGrpcCall.mockResolvedValue({
      success: true,
      task: null,
      message: 'Task not found',
    });

    const response = await GET({ params: { id: 'task-123' } } as any);
    const data = await response.json();

    expect(response.status).toBe(404);
    expect(data.success).toBe(false);
    expect(data.message).toBe('Task not found');
  });

  it('should handle gRPC ServiceError', async () => {
    const { GET } = await import('../tasks/[id]');

    const error: grpc.ServiceError = {
      code: grpc.status.NOT_FOUND,
      message: 'Task not found',
      details: '',
      name: 'ServiceError',
    };

    mockPromisifyGrpcCall.mockRejectedValue(error);
    mockIsServiceError.mockReturnValue(true);
    mockGrpcErrorToHttpStatus.mockReturnValue(404);

    const response = await GET({ params: { id: 'task-123' } } as any);
    const data = await response.json();

    expect(response.status).toBe(404);
    expect(data.success).toBe(false);
    expect(data.message).toBe('Task not found');
    expect(data.code).toBe(grpc.status.NOT_FOUND);
  });

  it('should handle unknown errors', async () => {
    const { GET } = await import('../tasks/[id]');

    const error = new Error('Unknown error');
    mockPromisifyGrpcCall.mockRejectedValue(error);
    mockIsServiceError.mockReturnValue(false);

    const response = await GET({ params: { id: 'task-123' } } as any);
    const data = await response.json();

    expect(response.status).toBe(500);
    expect(data.success).toBe(false);
    expect(data.message).toBe('Unknown error');
  });
});

