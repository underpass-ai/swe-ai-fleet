/**
 * Unit tests for GET /api/epics/[id] endpoint
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as grpc from '@grpc/grpc-js';
import * as grpcClientModule from '../../../lib/grpc-client';
import * as grpcRequestBuilders from '../../../lib/grpc-request-builders';

// Mock gRPC client module
vi.mock('../../../lib/grpc-client');
vi.mock('../../../lib/grpc-request-builders');

const mockBuildGetEpicRequest = vi.mocked(grpcRequestBuilders.buildGetEpicRequest);

describe('GET /api/epics/[id]', () => {
  let mockClient: any;
  let mockGetPlanningClient: any;
  let mockPromisifyGrpcCall: any;
  let mockGrpcErrorToHttpStatus: any;
  let mockIsServiceError: any;

  beforeEach(() => {
    vi.clearAllMocks();

    mockClient = {
      getEpic: vi.fn(),
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

    mockBuildGetEpicRequest.mockImplementation((payload) => payload as any);

    vi.mocked(grpcClientModule.getPlanningClient).mockImplementation(mockGetPlanningClient);
    vi.mocked(grpcClientModule.promisifyGrpcCall).mockImplementation(mockPromisifyGrpcCall);
    vi.mocked(grpcClientModule.grpcErrorToHttpStatus).mockImplementation(mockGrpcErrorToHttpStatus);
    vi.mocked(grpcClientModule.isServiceError).mockImplementation(mockIsServiceError);
  });

  it('should get epic by id successfully', async () => {
    const { GET } = await import('../epics/[id]');

    const mockResponse = {
      epic: {
        epic_id: 'epic-123',
        title: 'Test Epic',
        description: 'Description',
        project_id: 'proj-1',
      },
      success: true,
      message: 'Epic retrieved successfully',
    };

    mockPromisifyGrpcCall.mockResolvedValue(mockResponse);

    const response = await GET({ params: { id: 'epic-123' } } as any);
    const data = await response.json();

    expect(response.status).toBe(200);
    expect(data.success).toBe(true);
    expect(data.epic.epic_id).toBe('epic-123');
    expect(data.epic.title).toBe('Test Epic');
    expect(mockBuildGetEpicRequest).toHaveBeenCalledWith({ epic_id: 'epic-123' });
    expect(mockPromisifyGrpcCall).toHaveBeenCalledWith(
      expect.any(Function),
      expect.objectContaining({ epic_id: 'epic-123' })
    );
  });

  it('should return 400 when id is missing', async () => {
    const { GET } = await import('../epics/[id]');

    const response = await GET({ params: {} } as any);
    const data = await response.json();

    expect(response.status).toBe(400);
    expect(data.success).toBe(false);
    expect(data.message).toBe('epic_id is required');
  });

  it('should return 400 when id is undefined', async () => {
    const { GET } = await import('../epics/[id]');

    const response = await GET({ params: { id: undefined } } as any);
    const data = await response.json();

    expect(response.status).toBe(400);
    expect(data.success).toBe(false);
    expect(data.message).toBe('epic_id is required');
  });

  it('should return 404 when epic not found (success=false)', async () => {
    const { GET } = await import('../epics/[id]');

    mockPromisifyGrpcCall.mockResolvedValue({
      success: false,
      message: 'Epic not found',
    });

    const response = await GET({ params: { id: 'epic-123' } } as any);
    const data = await response.json();

    expect(response.status).toBe(404);
    expect(data.success).toBe(false);
    expect(data.message).toBe('Epic not found');
  });

  it('should return 404 when epic is null', async () => {
    const { GET } = await import('../epics/[id]');

    mockPromisifyGrpcCall.mockResolvedValue({
      success: true,
      epic: null,
      message: 'Epic not found',
    });

    const response = await GET({ params: { id: 'epic-123' } } as any);
    const data = await response.json();

    expect(response.status).toBe(404);
    expect(data.success).toBe(false);
    expect(data.message).toBe('Epic not found');
  });

  it('should handle gRPC ServiceError', async () => {
    const { GET } = await import('../epics/[id]');

    const error: grpc.ServiceError = {
      code: grpc.status.NOT_FOUND,
      message: 'Epic not found',
      details: '',
      name: 'ServiceError',
    };

    mockPromisifyGrpcCall.mockRejectedValue(error);
    mockIsServiceError.mockReturnValue(true);
    mockGrpcErrorToHttpStatus.mockReturnValue(404);

    const response = await GET({ params: { id: 'epic-123' } } as any);
    const data = await response.json();

    expect(response.status).toBe(404);
    expect(data.success).toBe(false);
    expect(data.message).toBe('Epic not found');
    expect(data.code).toBe(grpc.status.NOT_FOUND);
  });

  it('should handle unknown errors', async () => {
    const { GET } = await import('../epics/[id]');

    const error = new Error('Unknown error');
    mockPromisifyGrpcCall.mockRejectedValue(error);
    mockIsServiceError.mockReturnValue(false);

    const response = await GET({ params: { id: 'epic-123' } } as any);
    const data = await response.json();

    expect(response.status).toBe(500);
    expect(data.success).toBe(false);
    expect(data.message).toBe('Unknown error');
  });
});

