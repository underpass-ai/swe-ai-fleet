/**
 * Unit tests for Graph Relationships API route
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as grpc from '@grpc/grpc-js';
import * as contextGrpcClientModule from '../../../lib/context-grpc-client';

// Mock Context gRPC client module
vi.mock('../../../lib/context-grpc-client');

const mockGetContextClient = vi.mocked(contextGrpcClientModule.getContextClient);
const mockPromisifyGrpcCall = vi.mocked(contextGrpcClientModule.promisifyGrpcCall);
const mockGrpcErrorToHttpStatus = vi.mocked(contextGrpcClientModule.grpcErrorToHttpStatus);
const mockIsServiceError = vi.mocked(contextGrpcClientModule.isServiceError);

describe('Graph Relationships API Route', () => {
  let mockClient: any;
  let GET: any;

  beforeEach(async () => {
    vi.clearAllMocks();

    // Dynamically import the route handler
    const module = await import('../graph/relationships');
    GET = module.GET;

    mockClient = {
      getGraphRelationships: vi.fn(),
    };

    mockGetContextClient.mockReturnValue(mockClient as any);
    // Default implementation: will be overridden per test
    mockPromisifyGrpcCall.mockResolvedValue({
      success: true,
      node: { id: 'test', type: 'Story', labels: [], properties: {}, title: 'Test' },
      neighbors: [],
      relationships: [],
      message: 'Success',
    });
    mockGrpcErrorToHttpStatus.mockImplementation((error: grpc.ServiceError) => {
      if (error.code === grpc.status.NOT_FOUND) return 404;
      if (error.code === grpc.status.INVALID_ARGUMENT) return 400;
      return 500;
    });
    mockIsServiceError.mockImplementation((error: unknown) => {
      return (
        typeof error === 'object' &&
        error !== null &&
        'code' in error &&
        typeof (error as any).code === 'number'
      );
    });
  });

  describe('GET /api/graph/relationships', () => {
    it('should return graph relationships successfully', async () => {
      const mockResponse = {
        success: true,
        node: {
          id: 'story-123',
          type: 'Story',
          labels: ['Story'],
          properties: { story_id: 'story-123', title: 'Test Story' },
          title: 'Test Story',
        },
        neighbors: [
          {
            id: 'epic-001',
            type: 'Epic',
            labels: ['Epic'],
            properties: { epic_id: 'epic-001', title: 'Test Epic' },
            title: 'Test Epic',
          },
        ],
        relationships: [
          {
            from_node_id: 'epic-001',
            to_node_id: 'story-123',
            type: 'CONTAINS_STORY',
            properties: {},
          },
        ],
        message: 'Graph relationships retrieved successfully',
      };

      // Mock promisifyGrpcCall to return the mock response directly
      mockPromisifyGrpcCall.mockResolvedValueOnce(mockResponse);

      const request = new Request('http://localhost/api/graph/relationships?node_id=story-123&node_type=Story&depth=2');
      const response = await GET({ request } as any);
      const body = await response.json();

      expect(response.status).toBe(200);
      expect(body.success).toBe(true);
      expect(body.node.id).toBe('story-123');
      expect(body.node.title).toBe('Test Story');
      expect(body.neighbors).toHaveLength(1);
      expect(body.relationships).toHaveLength(1);
      expect(mockGetContextClient).toHaveBeenCalled();
    });

    it('should use default node_type when not provided', async () => {
      const mockResponse = {
        success: true,
        node: {
          id: 'story-123',
          type: 'Story',
          labels: ['Story'],
          properties: {},
          title: 'Test Story',
        },
        neighbors: [],
        relationships: [],
        message: 'Graph relationships retrieved successfully',
      };

      // Mock promisifyGrpcCall to return the mock response directly
      mockPromisifyGrpcCall.mockResolvedValueOnce(mockResponse);

      const request = new Request('http://localhost/api/graph/relationships?node_id=story-123');
      const response = await GET({ request } as any);
      const body = await response.json();

      expect(response.status).toBe(200);
      expect(body.success).toBe(true);
      // Verify promisifyGrpcCall was called (which calls getGraphRelationships)
      expect(mockPromisifyGrpcCall).toHaveBeenCalled();
    });

    it('should clamp depth between 1 and 3', async () => {
      const mockResponse = {
        success: true,
        node: {
          id: 'story-123',
          type: 'Story',
          labels: ['Story'],
          properties: {},
          title: 'Test Story',
        },
        neighbors: [],
        relationships: [],
        message: 'Graph relationships retrieved successfully',
      };

      // Mock promisifyGrpcCall to return the mock response directly
      mockPromisifyGrpcCall.mockResolvedValue(mockResponse);

      // Test depth > 3 (should clamp to 3)
      const request1 = new Request('http://localhost/api/graph/relationships?node_id=story-123&depth=5');
      const response1 = await GET({ request: request1 } as any);
      expect(response1.status).toBe(200);

      // Test depth < 1 (should clamp to 1)
      const request2 = new Request('http://localhost/api/graph/relationships?node_id=story-123&depth=0');
      const response2 = await GET({ request: request2 } as any);
      expect(response2.status).toBe(200);
    });

    it('should return 400 when node_id is missing', async () => {
      const request = new Request('http://localhost/api/graph/relationships?node_type=Story');
      const response = await GET({ request } as any);
      const body = await response.json();

      expect(response.status).toBe(400);
      expect(body.success).toBe(false);
      expect(body.message).toBe('node_id is required');
      expect(mockGetContextClient).not.toHaveBeenCalled();
    });

    it('should return 400 when response.success is false', async () => {
      const mockResponse = {
        success: false,
        message: 'Node not found',
      };

      // Mock promisifyGrpcCall to return the mock response directly
      mockPromisifyGrpcCall.mockResolvedValueOnce(mockResponse);

      const request = new Request('http://localhost/api/graph/relationships?node_id=story-123');
      const response = await GET({ request } as any);
      const body = await response.json();

      expect(response.status).toBe(400);
      expect(body.success).toBe(false);
      expect(body.message).toBe('Node not found');
    });

    it('should return 400 when response.success is false with empty message', async () => {
      const mockResponse = {
        success: false,
        message: '',
      };

      mockPromisifyGrpcCall.mockResolvedValueOnce(mockResponse);

      const request = new Request('http://localhost/api/graph/relationships?node_id=story-123');
      const response = await GET({ request } as any);
      const body = await response.json();

      expect(response.status).toBe(400);
      expect(body.success).toBe(false);
      expect(body.message).toBe('Failed to get graph relationships');
    });

    it('should handle missing node properties gracefully', async () => {
      const mockResponse = {
        success: true,
        node: undefined,
        neighbors: [],
        relationships: [],
        message: 'Graph relationships retrieved successfully',
      };

      // Mock promisifyGrpcCall to return the mock response directly
      mockPromisifyGrpcCall.mockResolvedValueOnce(mockResponse);

      const request = new Request('http://localhost/api/graph/relationships?node_id=story-123&node_type=Story');
      const response = await GET({ request } as any);
      const body = await response.json();

      expect(response.status).toBe(200);
      expect(body.success).toBe(true);
      expect(body.node.id).toBe('story-123'); // Falls back to node_id from query
      expect(body.node.title).toBe('story-123'); // Falls back to node_id
    });

    it('should handle missing neighbor properties gracefully', async () => {
      const mockResponse = {
        success: true,
        node: {
          id: 'story-123',
          type: 'Story',
          labels: ['Story'],
          properties: {},
          title: 'Test Story',
        },
        neighbors: [
          {
            id: 'epic-001',
            type: undefined,
            labels: undefined,
            properties: undefined,
            title: undefined,
          },
        ],
        relationships: [],
        message: 'Graph relationships retrieved successfully',
      };

      // Mock promisifyGrpcCall to return the mock response directly
      mockPromisifyGrpcCall.mockResolvedValueOnce(mockResponse);

      const request = new Request('http://localhost/api/graph/relationships?node_id=story-123&node_type=Story');
      const response = await GET({ request } as any);
      const body = await response.json();

      expect(response.status).toBe(200);
      expect(body.success).toBe(true);
      expect(body.neighbors).toHaveLength(1);
      expect(body.neighbors[0].id).toBe('epic-001');
      expect(body.neighbors[0].type).toBeUndefined();
      expect(body.neighbors[0].labels).toEqual([]);
      expect(body.neighbors[0].properties).toEqual({});
      expect(body.neighbors[0].title).toBe('epic-001'); // Falls back to id
    });

    it('should handle neighbors array with null/undefined values', async () => {
      const mockResponse = {
        success: true,
        node: {
          id: 'story-123',
          type: 'Story',
          labels: ['Story'],
          properties: {},
          title: 'Test Story',
        },
        neighbors: null,
        relationships: [],
        message: 'Graph relationships retrieved successfully',
      };

      mockPromisifyGrpcCall.mockResolvedValueOnce(mockResponse);

      const request = new Request('http://localhost/api/graph/relationships?node_id=story-123&node_type=Story');
      const response = await GET({ request } as any);
      const body = await response.json();

      expect(response.status).toBe(200);
      expect(body.neighbors).toEqual([]);
    });

    it('should handle relationships array with null/undefined values', async () => {
      const mockResponse = {
        success: true,
        node: {
          id: 'story-123',
          type: 'Story',
          labels: ['Story'],
          properties: {},
          title: 'Test Story',
        },
        neighbors: [],
        relationships: null,
        message: 'Graph relationships retrieved successfully',
      };

      mockPromisifyGrpcCall.mockResolvedValueOnce(mockResponse);

      const request = new Request('http://localhost/api/graph/relationships?node_id=story-123&node_type=Story');
      const response = await GET({ request } as any);
      const body = await response.json();

      expect(response.status).toBe(200);
      expect(body.relationships).toEqual([]);
    });

    it('should handle empty message in successful response', async () => {
      const mockResponse = {
        success: true,
        node: {
          id: 'story-123',
          type: 'Story',
          labels: ['Story'],
          properties: {},
          title: 'Test Story',
        },
        neighbors: [],
        relationships: [],
        message: '',
      };

      mockPromisifyGrpcCall.mockResolvedValueOnce(mockResponse);

      const request = new Request('http://localhost/api/graph/relationships?node_id=story-123&node_type=Story');
      const response = await GET({ request } as any);
      const body = await response.json();

      expect(response.status).toBe(200);
      expect(body.message).toBe('Graph relationships retrieved successfully');
    });

    it('should handle gRPC service errors', async () => {
      const grpcError: grpc.ServiceError = {
        code: grpc.status.NOT_FOUND,
        details: 'Node not found',
        message: 'Node not found',
        name: 'ServiceError',
        metadata: new grpc.Metadata(),
      };

      mockPromisifyGrpcCall.mockRejectedValueOnce(grpcError);

      const request = new Request('http://localhost/api/graph/relationships?node_id=story-123&node_type=Story');
      const response = await GET({ request } as any);
      const body = await response.json();

      expect(response.status).toBe(404);
      expect(body.success).toBe(false);
      expect(body.message).toBe('Node not found');
      expect(body.code).toBe(grpc.status.NOT_FOUND);
      expect(mockGrpcErrorToHttpStatus).toHaveBeenCalledWith(grpcError);
    });

    it('should handle gRPC INVALID_ARGUMENT errors', async () => {
      const grpcError: grpc.ServiceError = {
        code: grpc.status.INVALID_ARGUMENT,
        details: 'Invalid node_type',
        message: 'Invalid node_type',
        name: 'ServiceError',
        metadata: new grpc.Metadata(),
      };

      mockPromisifyGrpcCall.mockRejectedValueOnce(grpcError);

      const request = new Request('http://localhost/api/graph/relationships?node_id=story-123&node_type=Invalid');
      const response = await GET({ request } as any);
      const body = await response.json();

      expect(response.status).toBe(400);
      expect(body.success).toBe(false);
      expect(body.message).toBe('Invalid node_type');
      expect(body.code).toBe(grpc.status.INVALID_ARGUMENT);
    });

    it('should handle unknown errors', async () => {
      const unknownError = new Error('Unknown error');

      mockPromisifyGrpcCall.mockRejectedValueOnce(unknownError);

      const request = new Request('http://localhost/api/graph/relationships?node_id=story-123&node_type=Story');
      const response = await GET({ request } as any);
      const body = await response.json();

      expect(response.status).toBe(500);
      expect(body.success).toBe(false);
      expect(body.message).toBe('Unknown error');
      expect(mockIsServiceError).toHaveBeenCalledWith(unknownError);
    });

    it('should handle non-Error objects', async () => {
      const nonError = { message: 'Something went wrong' };

      mockPromisifyGrpcCall.mockRejectedValueOnce(nonError);

      const request = new Request('http://localhost/api/graph/relationships?node_id=story-123&node_type=Story');
      const response = await GET({ request } as any);
      const body = await response.json();

      expect(response.status).toBe(500);
      expect(body.success).toBe(false);
      expect(body.message).toBe('Unknown error');
    });

    it('should map relationships correctly', async () => {
      const mockResponse = {
        success: true,
        node: {
          id: 'story-123',
          type: 'Story',
          labels: ['Story'],
          properties: {},
          title: 'Test Story',
        },
        neighbors: [
          {
            id: 'task-001',
            type: 'Task',
            labels: ['Task'],
            properties: {},
            title: 'Test Task',
          },
        ],
        relationships: [
          {
            from_node_id: 'story-123',
            to_node_id: 'task-001',
            type: 'HAS_TASK',
            properties: { created_at: '2025-01-01' },
          },
        ],
        message: 'Graph relationships retrieved successfully',
      };

      // Mock promisifyGrpcCall to return the mock response directly
      mockPromisifyGrpcCall.mockResolvedValueOnce(mockResponse);

      const request = new Request('http://localhost/api/graph/relationships?node_id=story-123&node_type=Story');
      const response = await GET({ request } as any);
      const body = await response.json();

      expect(response.status).toBe(200);
      expect(body.relationships).toHaveLength(1);
      expect(body.relationships[0].from_node_id).toBe('story-123');
      expect(body.relationships[0].to_node_id).toBe('task-001');
      expect(body.relationships[0].type).toBe('HAS_TASK');
      expect(body.relationships[0].properties).toEqual({ created_at: '2025-01-01' });
    });
  });
});

