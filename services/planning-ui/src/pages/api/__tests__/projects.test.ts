/**
 * Unit tests for Projects API routes
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as grpc from '@grpc/grpc-js';
import * as grpcClientModule from '../../../lib/grpc-client';
import * as grpcRequestBuilders from '../../../lib/grpc-request-builders';

// Mock gRPC client module
vi.mock('../../../lib/grpc-client');
vi.mock('../../../lib/grpc-request-builders');

const mockBuildListProjectsRequest = vi.mocked(grpcRequestBuilders.buildListProjectsRequest);
const mockBuildCreateProjectRequest = vi.mocked(grpcRequestBuilders.buildCreateProjectRequest);
const mockBuildGetProjectRequest = vi.mocked(grpcRequestBuilders.buildGetProjectRequest);

describe('Projects API Routes', () => {
  let mockClient: any;
  let mockGetPlanningClient: any;
  let mockPromisifyGrpcCall: any;
  let mockGrpcErrorToHttpStatus: any;
  let mockIsServiceError: any;

  beforeEach(() => {
    // Reset mocks
    vi.clearAllMocks();

    // Setup mock client
    mockClient = {
      listProjects: vi.fn(),
      createProject: vi.fn(),
      getProject: vi.fn(),
    };

    // Setup mock functions
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

    mockBuildListProjectsRequest.mockImplementation((payload) => payload as any);
    mockBuildCreateProjectRequest.mockImplementation((payload) => payload as any);
    mockBuildGetProjectRequest.mockImplementation((payload) => payload as any);

    vi.mocked(grpcClientModule.getPlanningClient).mockImplementation(mockGetPlanningClient);
    vi.mocked(grpcClientModule.promisifyGrpcCall).mockImplementation(mockPromisifyGrpcCall);
    vi.mocked(grpcClientModule.grpcErrorToHttpStatus).mockImplementation(mockGrpcErrorToHttpStatus);
    vi.mocked(grpcClientModule.isServiceError).mockImplementation(mockIsServiceError);
  });

  describe('GET /api/projects', () => {
    it('should list projects successfully', async () => {
      const { GET } = await import('../projects/index');

      const mockResponse = {
        projects: [
          { project_id: 'proj-1', name: 'Project 1', owner: 'user1' },
          { project_id: 'proj-2', name: 'Project 2', owner: 'user2' },
        ],
        total_count: 2,
        success: true,
        message: 'Projects retrieved',
      };

      mockPromisifyGrpcCall.mockResolvedValue(mockResponse);

      const request = new Request('http://localhost/api/projects');
      const response = await GET({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(data.projects).toHaveLength(2);
      expect(data.total_count).toBe(2);
      expect(mockBuildListProjectsRequest).toHaveBeenCalledWith(
        expect.objectContaining({
          limit: 100,
          offset: 0,
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

    it('should handle query parameters (limit, offset, status_filter)', async () => {
      const { GET } = await import('../projects/index');

      mockPromisifyGrpcCall.mockResolvedValue({
        projects: [],
        total_count: 0,
        success: true,
      });

      const request = new Request(
        'http://localhost/api/projects?limit=50&offset=10&status_filter=active'
      );
      const response = await GET({ request } as any);

      expect(response.status).toBe(200);
      expect(mockBuildListProjectsRequest).toHaveBeenCalledWith(
        expect.objectContaining({
          limit: 50,
          offset: 10,
          status_filter: 'active',
        })
      );
      expect(mockPromisifyGrpcCall).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          limit: 50,
          offset: 10,
          status_filter: 'active',
        })
      );
    });

    it('should handle empty projects list', async () => {
      const { GET } = await import('../projects/index');

      mockPromisifyGrpcCall.mockResolvedValue({
        projects: [],
        total_count: 0,
        success: true,
      });

      const request = new Request('http://localhost/api/projects');
      const response = await GET({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.projects).toEqual([]);
      expect(data.total_count).toBe(0);
    });

    it('should handle gRPC ServiceError', async () => {
      const { GET } = await import('../projects/index');

      const error: grpc.ServiceError = {
        code: grpc.status.NOT_FOUND,
        message: 'Projects not found',
        details: '',
        name: 'ServiceError',
      };

      mockPromisifyGrpcCall.mockRejectedValue(error);
      mockIsServiceError.mockReturnValue(true);
      mockGrpcErrorToHttpStatus.mockReturnValue(404);

      const request = new Request('http://localhost/api/projects');
      const response = await GET({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(404);
      expect(data.success).toBe(false);
      expect(data.message).toBe('Projects not found');
      expect(data.code).toBe(grpc.status.NOT_FOUND);
    });

    it('should handle unknown errors', async () => {
      const { GET } = await import('../projects/index');

      const error = new Error('Unknown error');
      mockPromisifyGrpcCall.mockRejectedValue(error);
      mockIsServiceError.mockReturnValue(false);

      const request = new Request('http://localhost/api/projects');
      const response = await GET({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(500);
      expect(data.success).toBe(false);
      expect(data.message).toBe('Unknown error');
    });
  });

  describe('POST /api/projects', () => {
    it('should create project successfully', async () => {
      const { POST } = await import('../projects/index');

      const mockResponse = {
        project: {
          project_id: 'proj-123',
          name: 'New Project',
          description: 'Description',
          owner: 'user1',
        },
        success: true,
        message: 'Project created',
      };

      mockPromisifyGrpcCall.mockResolvedValue(mockResponse);

      const request = new Request('http://localhost/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'New Project',
          description: 'Description',
          owner: 'user1',
        }),
      });

      const response = await POST({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(201);
      expect(data.success).toBe(true);
      expect(data.project.project_id).toBe('proj-123');
      expect(mockBuildCreateProjectRequest).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'New Project',
          description: 'Description',
          owner: 'user1',
        })
      );
      expect(mockPromisifyGrpcCall).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          name: 'New Project',
          description: 'Description',
          owner: 'user1',
        })
      );
    });

    it('should reject missing required fields (name)', async () => {
      const { POST } = await import('../projects/index');

      const request = new Request('http://localhost/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description: 'Description',
          owner: 'user1',
        }),
      });

      const response = await POST({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.message).toBe('name and owner are required');
    });

    it('should reject missing required fields (owner)', async () => {
      const { POST } = await import('../projects/index');

      const request = new Request('http://localhost/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'New Project',
          description: 'Description',
        }),
      });

      const response = await POST({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.message).toBe('name and owner are required');
    });

    it('should use empty string for optional description', async () => {
      const { POST } = await import('../projects/index');

      mockPromisifyGrpcCall.mockResolvedValue({
        project: { project_id: 'proj-123', name: 'Project', owner: 'user1' },
        success: true,
      });

      const request = new Request('http://localhost/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'Project',
          owner: 'user1',
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
      const { POST } = await import('../projects/index');

      const error: grpc.ServiceError = {
        code: grpc.status.INVALID_ARGUMENT,
        message: 'Invalid project data',
        details: '',
        name: 'ServiceError',
      };

      mockPromisifyGrpcCall.mockRejectedValue(error);
      mockIsServiceError.mockReturnValue(true);
      mockGrpcErrorToHttpStatus.mockReturnValue(400);

      const request = new Request('http://localhost/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'Project',
          owner: 'user1',
        }),
      });

      const response = await POST({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.message).toBe('Invalid project data');
    });

    it('should handle failed project creation (success=false)', async () => {
      const { POST } = await import('../projects/index');

      mockPromisifyGrpcCall.mockResolvedValue({
        success: false,
        message: 'Failed to create project',
      });

      const request = new Request('http://localhost/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'Project',
          owner: 'user1',
        }),
      });

      const response = await POST({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.message).toBe('Failed to create project');
    });
  });

  describe('GET /api/projects/[id]', () => {
    it('should get project by ID successfully', async () => {
      const { GET } = await import('../projects/[id]');

      const mockResponse = {
        project: {
          project_id: 'proj-123',
          name: 'Project 1',
          description: 'Description',
          owner: 'user1',
        },
        success: true,
        message: 'Project retrieved',
      };

      mockPromisifyGrpcCall.mockResolvedValue(mockResponse);

      const response = await GET({ params: { id: 'proj-123' } } as any);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(data.project.project_id).toBe('proj-123');
      expect(mockBuildGetProjectRequest).toHaveBeenCalledWith({ project_id: 'proj-123' });
      expect(mockPromisifyGrpcCall).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          project_id: 'proj-123',
        })
      );
    });

    it('should reject missing project_id', async () => {
      const { GET } = await import('../projects/[id]');

      const response = await GET({ params: {} } as any);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.message).toBe('project_id is required');
    });

    it('should handle project not found (success=false)', async () => {
      const { GET } = await import('../projects/[id]');

      mockPromisifyGrpcCall.mockResolvedValue({
        success: false,
        message: 'Project not found',
      });

      const response = await GET({ params: { id: 'proj-123' } } as any);
      const data = await response.json();

      expect(response.status).toBe(404);
      expect(data.success).toBe(false);
      expect(data.message).toBe('Project not found');
    });

    it('should handle gRPC ServiceError', async () => {
      const { GET } = await import('../projects/[id]');

      const error: grpc.ServiceError = {
        code: grpc.status.NOT_FOUND,
        message: 'Project not found',
        details: '',
        name: 'ServiceError',
      };

      mockPromisifyGrpcCall.mockRejectedValue(error);
      mockIsServiceError.mockReturnValue(true);
      mockGrpcErrorToHttpStatus.mockReturnValue(404);

      const response = await GET({ params: { id: 'proj-123' } } as any);
      const data = await response.json();

      expect(response.status).toBe(404);
      expect(data.success).toBe(false);
      expect(data.message).toBe('Project not found');
    });

    it('should handle error without message property', async () => {
      const { GET } = await import('../projects/[id]');

      const error: grpc.ServiceError = {
        code: grpc.status.NOT_FOUND,
        message: undefined as any,
        details: '',
        name: 'ServiceError',
      };

      mockPromisifyGrpcCall.mockRejectedValue(error);
      mockIsServiceError.mockReturnValue(true);
      mockGrpcErrorToHttpStatus.mockReturnValue(404);

      const response = await GET({ params: { id: 'proj-123' } } as any);
      const data = await response.json();

      expect(response.status).toBe(404);
      expect(data.success).toBe(false);
      expect(data.message).toBe('gRPC error');
    });

    it('should handle non-Error objects', async () => {
      const { GET } = await import('../projects/[id]');

      const error = { someProperty: 'value' };
      mockPromisifyGrpcCall.mockRejectedValue(error);
      mockIsServiceError.mockReturnValue(false);

      const response = await GET({ params: { id: 'proj-123' } } as any);
      const data = await response.json();

      expect(response.status).toBe(500);
      expect(data.success).toBe(false);
      expect(data.message).toBe('Unknown error');
    });

    it('should handle response with success=false but project exists', async () => {
      const { GET } = await import('../projects/[id]');

      mockPromisifyGrpcCall.mockResolvedValue({
        success: false,
        project: { project_id: 'proj-123', name: 'Project' },
        message: 'Error message',
      });

      const response = await GET({ params: { id: 'proj-123' } } as any);
      const data = await response.json();

      expect(response.status).toBe(404);
      expect(data.success).toBe(false);
    });

    it('should handle response with success=true but no project', async () => {
      const { GET } = await import('../projects/[id]');

      mockPromisifyGrpcCall.mockResolvedValue({
        success: true,
        project: null,
        message: 'Success but no project',
      });

      const response = await GET({ params: { id: 'proj-123' } } as any);
      const data = await response.json();

      expect(response.status).toBe(404);
      expect(data.success).toBe(false);
    });
  });
});

