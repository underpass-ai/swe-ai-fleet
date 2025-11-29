/**
 * Unit tests for Epics API routes
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as grpc from '@grpc/grpc-js';
import * as grpcClientModule from '../../../lib/grpc-client';
import * as grpcRequestBuilders from '../../../lib/grpc-request-builders';

// Mock gRPC client module
vi.mock('../../../lib/grpc-client');
vi.mock('../../../lib/grpc-request-builders');

const mockBuildListEpicsRequest = vi.mocked(grpcRequestBuilders.buildListEpicsRequest);
const mockBuildCreateEpicRequest = vi.mocked(grpcRequestBuilders.buildCreateEpicRequest);

describe('Epics API Routes', () => {
  let mockClient: any;
  let mockGetPlanningClient: any;
  let mockPromisifyGrpcCall: any;
  let mockGrpcErrorToHttpStatus: any;
  let mockIsServiceError: any;

  beforeEach(() => {
    vi.clearAllMocks();

    mockClient = {
      ListEpics: vi.fn(),
      CreateEpic: vi.fn(),
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

    mockBuildListEpicsRequest.mockImplementation((payload) => payload as any);
    mockBuildCreateEpicRequest.mockImplementation((payload) => payload as any);

    vi.mocked(grpcClientModule.getPlanningClient).mockImplementation(mockGetPlanningClient);
    vi.mocked(grpcClientModule.promisifyGrpcCall).mockImplementation(mockPromisifyGrpcCall);
    vi.mocked(grpcClientModule.grpcErrorToHttpStatus).mockImplementation(mockGrpcErrorToHttpStatus);
    vi.mocked(grpcClientModule.isServiceError).mockImplementation(mockIsServiceError);
  });

  describe('GET /api/epics', () => {
    it('should list epics successfully', async () => {
      const { GET } = await import('../epics/index');

      const mockResponse = {
        epics: [
          { epic_id: 'epic-1', title: 'Epic 1', project_id: 'proj-1' },
          { epic_id: 'epic-2', title: 'Epic 2', project_id: 'proj-1' },
        ],
        total_count: 2,
        success: true,
        message: 'Epics retrieved',
      };

      mockPromisifyGrpcCall.mockResolvedValue(mockResponse);

      const request = new Request('http://localhost/api/epics');
      const response = await GET({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(data.epics).toHaveLength(2);
      expect(data.total_count).toBe(2);
      expect(mockBuildListEpicsRequest).toHaveBeenCalledWith(
        expect.objectContaining({
          limit: 100,
          offset: 0,
          project_id: undefined,
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

    it('should handle query parameters (project_id, status_filter, limit, offset)', async () => {
      const { GET } = await import('../epics/index');

      mockPromisifyGrpcCall.mockResolvedValue({
        epics: [],
        total_count: 0,
        success: true,
      });

      const request = new Request(
        'http://localhost/api/epics?project_id=proj-1&status_filter=active&limit=50&offset=10'
      );
      const response = await GET({ request } as any);

      expect(response.status).toBe(200);
      expect(mockBuildListEpicsRequest).toHaveBeenCalledWith(
        expect.objectContaining({
          project_id: 'proj-1',
          status_filter: 'active',
          limit: 50,
          offset: 10,
        })
      );
      expect(mockPromisifyGrpcCall).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          project_id: 'proj-1',
          status_filter: 'active',
          limit: 50,
          offset: 10,
        })
      );
    });

    it('should handle empty epics list', async () => {
      const { GET } = await import('../epics/index');

      mockPromisifyGrpcCall.mockResolvedValue({
        epics: [],
        total_count: 0,
        success: true,
      });

      const request = new Request('http://localhost/api/epics');
      const response = await GET({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.epics).toEqual([]);
      expect(data.total_count).toBe(0);
    });

    it('should handle gRPC ServiceError', async () => {
      const { GET } = await import('../epics/index');

      const error: grpc.ServiceError = {
        code: grpc.status.NOT_FOUND,
        message: 'Epics not found',
        details: '',
        name: 'ServiceError',
      };

      mockPromisifyGrpcCall.mockRejectedValue(error);
      mockIsServiceError.mockReturnValue(true);
      mockGrpcErrorToHttpStatus.mockReturnValue(404);

      const request = new Request('http://localhost/api/epics');
      const response = await GET({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(404);
      expect(data.success).toBe(false);
      expect(data.message).toBe('Epics not found');
    });

    it('should handle unknown errors', async () => {
      const { GET } = await import('../epics/index');

      const error = new Error('Unknown error');
      mockPromisifyGrpcCall.mockRejectedValue(error);
      mockIsServiceError.mockReturnValue(false);

      const request = new Request('http://localhost/api/epics');
      const response = await GET({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(500);
      expect(data.success).toBe(false);
      expect(data.message).toBe('Unknown error');
    });
  });

  describe('POST /api/epics', () => {
    it('should create epic successfully', async () => {
      const { POST } = await import('../epics/index');

      const mockResponse = {
        epic: {
          epic_id: 'epic-123',
          title: 'New Epic',
          description: 'Description',
          project_id: 'proj-1',
        },
        success: true,
        message: 'Epic created',
      };

      mockPromisifyGrpcCall.mockResolvedValue(mockResponse);

      const request = new Request('http://localhost/api/epics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: 'proj-1',
          title: 'New Epic',
          description: 'Description',
        }),
      });

      const response = await POST({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(201);
      expect(data.success).toBe(true);
      expect(data.epic.epic_id).toBe('epic-123');
      expect(mockBuildCreateEpicRequest).toHaveBeenCalledWith(
        expect.objectContaining({
          project_id: 'proj-1',
          title: 'New Epic',
          description: 'Description',
        })
      );
      expect(mockPromisifyGrpcCall).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          project_id: 'proj-1',
          title: 'New Epic',
          description: 'Description',
        })
      );
    });

    it('should reject missing required fields (project_id)', async () => {
      const { POST } = await import('../epics/index');

      const request = new Request('http://localhost/api/epics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: 'Epic',
          description: 'Description',
        }),
      });

      const response = await POST({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.message).toBe('project_id and title are required');
    });

    it('should reject missing required fields (title)', async () => {
      const { POST } = await import('../epics/index');

      const request = new Request('http://localhost/api/epics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: 'proj-1',
          description: 'Description',
        }),
      });

      const response = await POST({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.message).toBe('project_id and title are required');
    });

    it('should use empty string for optional description', async () => {
      const { POST } = await import('../epics/index');

      mockPromisifyGrpcCall.mockResolvedValue({
        epic: { epic_id: 'epic-123', title: 'Epic', project_id: 'proj-1' },
        success: true,
      });

      const request = new Request('http://localhost/api/epics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: 'proj-1',
          title: 'Epic',
        }),
      });

      await POST({ request } as any);

      expect(mockPromisifyGrpcCall).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          description: '',
        })
      );
    });

    it('should handle gRPC ServiceError', async () => {
      const { POST } = await import('../epics/index');

      const error: grpc.ServiceError = {
        code: grpc.status.INVALID_ARGUMENT,
        message: 'Invalid epic data',
        details: '',
        name: 'ServiceError',
      };

      mockPromisifyGrpcCall.mockRejectedValue(error);
      mockIsServiceError.mockReturnValue(true);
      mockGrpcErrorToHttpStatus.mockReturnValue(400);

      const request = new Request('http://localhost/api/epics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: 'proj-1',
          title: 'Epic',
        }),
      });

      const response = await POST({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.message).toBe('Invalid epic data');
    });

    it('should handle failed epic creation (success=false)', async () => {
      const { POST } = await import('../epics/index');

      mockPromisifyGrpcCall.mockResolvedValue({
        success: false,
        message: 'Failed to create epic',
      });

      const request = new Request('http://localhost/api/epics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: 'proj-1',
          title: 'Epic',
        }),
      });

      const response = await POST({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.message).toBe('Failed to create epic');
    });
  });
});


