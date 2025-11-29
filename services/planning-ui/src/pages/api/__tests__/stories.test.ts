/**
 * Unit tests for Stories API routes
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as grpc from '@grpc/grpc-js';
import * as grpcClientModule from '../../../lib/grpc-client';
import * as grpcRequestBuilders from '../../../lib/grpc-request-builders';

// Mock gRPC client module
vi.mock('../../../lib/grpc-client');
vi.mock('../../../lib/grpc-request-builders');

const mockBuildListStoriesRequest = vi.mocked(grpcRequestBuilders.buildListStoriesRequest);
const mockBuildCreateStoryRequest = vi.mocked(grpcRequestBuilders.buildCreateStoryRequest);
const mockBuildGetStoryRequest = vi.mocked(grpcRequestBuilders.buildGetStoryRequest);
const mockBuildTransitionStoryRequest = vi.mocked(grpcRequestBuilders.buildTransitionStoryRequest);

describe('Stories API Routes', () => {
  let mockClient: any;
  let mockGetPlanningClient: any;
  let mockPromisifyGrpcCall: any;
  let mockGrpcErrorToHttpStatus: any;
  let mockIsServiceError: any;

  beforeEach(() => {
    vi.clearAllMocks();

    mockClient = {
      ListStories: vi.fn(),
      CreateStory: vi.fn(),
      GetStory: vi.fn(),
      TransitionStory: vi.fn(),
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

    mockBuildListStoriesRequest.mockImplementation((payload) => payload as any);
    mockBuildCreateStoryRequest.mockImplementation((payload) => payload as any);
    mockBuildGetStoryRequest.mockImplementation((payload) => payload as any);
    mockBuildTransitionStoryRequest.mockImplementation((payload) => payload as any);

    vi.mocked(grpcClientModule.getPlanningClient).mockImplementation(mockGetPlanningClient);
    vi.mocked(grpcClientModule.promisifyGrpcCall).mockImplementation(mockPromisifyGrpcCall);
    vi.mocked(grpcClientModule.grpcErrorToHttpStatus).mockImplementation(mockGrpcErrorToHttpStatus);
    vi.mocked(grpcClientModule.isServiceError).mockImplementation(mockIsServiceError);
  });

  describe('GET /api/stories', () => {
    it('should list stories successfully', async () => {
      const { GET } = await import('../stories/index');

      const mockResponse = {
        stories: [
          { story_id: 'story-1', title: 'Story 1', state: 'draft' },
          { story_id: 'story-2', title: 'Story 2', state: 'in_progress' },
        ],
        total_count: 2,
        success: true,
        message: 'Stories retrieved',
      };

      mockPromisifyGrpcCall.mockResolvedValue(mockResponse);

      const request = new Request('http://localhost/api/stories');
      const response = await GET({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(data.stories).toHaveLength(2);
      expect(data.total_count).toBe(2);
      expect(mockBuildListStoriesRequest).toHaveBeenCalledWith(
        expect.objectContaining({
          limit: 100,
          offset: 0,
          state_filter: undefined,
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

    it('should handle query parameters (state, limit, offset)', async () => {
      const { GET } = await import('../stories/index');

      mockPromisifyGrpcCall.mockResolvedValue({
        stories: [],
        total_count: 0,
        success: true,
      });

      const request = new Request(
        'http://localhost/api/stories?state=draft&limit=50&offset=10'
      );
      const response = await GET({ request } as any);

      expect(response.status).toBe(200);
      expect(mockBuildListStoriesRequest).toHaveBeenCalledWith(
        expect.objectContaining({
          state_filter: 'draft',
          limit: 50,
          offset: 10,
        })
      );
      expect(mockPromisifyGrpcCall).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          state_filter: 'draft',
          limit: 50,
          offset: 10,
        })
      );
    });

    it('should handle empty stories list', async () => {
      const { GET } = await import('../stories/index');

      mockPromisifyGrpcCall.mockResolvedValue({
        stories: [],
        total_count: 0,
        success: true,
      });

      const request = new Request('http://localhost/api/stories');
      const response = await GET({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.stories).toEqual([]);
      expect(data.total_count).toBe(0);
    });

    it('should handle gRPC ServiceError', async () => {
      const { GET } = await import('../stories/index');

      const error: grpc.ServiceError = {
        code: grpc.status.NOT_FOUND,
        message: 'Stories not found',
        details: '',
        name: 'ServiceError',
      };

      mockPromisifyGrpcCall.mockRejectedValue(error);
      mockIsServiceError.mockReturnValue(true);
      mockGrpcErrorToHttpStatus.mockReturnValue(404);

      const request = new Request('http://localhost/api/stories');
      const response = await GET({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(404);
      expect(data.success).toBe(false);
      expect(data.message).toBe('Stories not found');
    });
  });

  describe('POST /api/stories', () => {
    it('should create story successfully', async () => {
      const { POST } = await import('../stories/index');

      const mockResponse = {
        story: {
          story_id: 'story-123',
          title: 'New Story',
          brief: 'Brief',
          epic_id: 'epic-1',
        },
        success: true,
        message: 'Story created',
      };

      mockPromisifyGrpcCall.mockResolvedValue(mockResponse);

      const request = new Request('http://localhost/api/stories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          epic_id: 'epic-1',
          title: 'New Story',
          brief: 'Brief',
          created_by: 'user1',
        }),
      });

      const response = await POST({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(201);
      expect(data.success).toBe(true);
      expect(data.story.story_id).toBe('story-123');
      expect(mockBuildCreateStoryRequest).toHaveBeenCalledWith(
        expect.objectContaining({
          epic_id: 'epic-1',
          title: 'New Story',
          brief: 'Brief',
          created_by: 'user1',
        })
      );
      expect(mockPromisifyGrpcCall).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          epic_id: 'epic-1',
          title: 'New Story',
          brief: 'Brief',
          created_by: 'user1',
        })
      );
    });

    it('should reject missing required fields (epic_id)', async () => {
      const { POST } = await import('../stories/index');

      const request = new Request('http://localhost/api/stories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: 'Story',
          brief: 'Brief',
        }),
      });

      const response = await POST({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.message).toBe('epic_id and title are required');
    });

    it('should reject missing required fields (title)', async () => {
      const { POST } = await import('../stories/index');

      const request = new Request('http://localhost/api/stories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          epic_id: 'epic-1',
          brief: 'Brief',
        }),
      });

      const response = await POST({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.message).toBe('epic_id and title are required');
    });

    it('should reject empty brief', async () => {
      const { POST } = await import('../stories/index');

      const request = new Request('http://localhost/api/stories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          epic_id: 'epic-1',
          title: 'Story Title',
          brief: '', // Empty brief should be rejected
        }),
      });

      const response = await POST({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.message).toBe('brief is required and cannot be empty');
    });

    it('should reject whitespace-only brief', async () => {
      const { POST } = await import('../stories/index');

      const request = new Request('http://localhost/api/stories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          epic_id: 'epic-1',
          title: 'Story Title',
          brief: '   ', // Whitespace-only brief should be rejected
        }),
      });

      const response = await POST({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.message).toBe('brief is required and cannot be empty');
    });

    it('should use defaults for optional fields', async () => {
      const { POST } = await import('../stories/index');

      mockPromisifyGrpcCall.mockResolvedValue({
        story: { story_id: 'story-123', title: 'Story', epic_id: 'epic-1' },
        success: true,
      });

      const request = new Request('http://localhost/api/stories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          epic_id: 'epic-1',
          title: 'Story',
          brief: 'Story description', // brief is now required
        }),
      });

      await POST({ request } as any);

      expect(mockBuildCreateStoryRequest).toHaveBeenCalledWith(
        expect.objectContaining({
          brief: 'Story description',
          created_by: 'ui-user',
        })
      );
      expect(mockPromisifyGrpcCall).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          brief: 'Story description',
          created_by: 'ui-user',
        })
      );
    });

    it('should handle gRPC ServiceError', async () => {
      const { POST } = await import('../stories/index');

      const error: grpc.ServiceError = {
        code: grpc.status.INVALID_ARGUMENT,
        message: 'Invalid story data',
        details: 'Invalid story data',
        name: 'ServiceError',
      };

      mockPromisifyGrpcCall.mockRejectedValue(error);
      mockIsServiceError.mockReturnValue(true);
      mockGrpcErrorToHttpStatus.mockReturnValue(400);

      const request = new Request('http://localhost/api/stories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          epic_id: 'epic-1',
          title: 'Story',
          brief: 'Story description', // brief is now required
        }),
      });

      const response = await POST({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.message).toBe('Invalid story data');
    });

    it('should handle error without message property', async () => {
      const { POST } = await import('../stories/index');

      const error: grpc.ServiceError = {
        code: grpc.status.INVALID_ARGUMENT,
        message: undefined as any,
        details: '',
        name: 'ServiceError',
      };

      mockPromisifyGrpcCall.mockRejectedValue(error);
      mockIsServiceError.mockReturnValue(true);
      mockGrpcErrorToHttpStatus.mockReturnValue(400);

      const request = new Request('http://localhost/api/stories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          epic_id: 'epic-1',
          title: 'Story',
          brief: 'Story description', // brief is now required
        }),
      });

      const response = await POST({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.message).toBe('gRPC error');
    });

    it('should handle non-Error objects', async () => {
      const { POST } = await import('../stories/index');

      const error = { someProperty: 'value' };
      mockPromisifyGrpcCall.mockRejectedValue(error);
      mockIsServiceError.mockReturnValue(false);

      const request = new Request('http://localhost/api/stories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          epic_id: 'epic-1',
          title: 'Story',
          brief: 'Story description', // brief is now required
        }),
      });

      const response = await POST({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(500);
      expect(data.success).toBe(false);
      expect(data.message).toBe('Unknown error');
    });

    it('should handle response with success=false but story exists', async () => {
      const { POST } = await import('../stories/index');

      mockPromisifyGrpcCall.mockResolvedValue({
        success: false,
        story: { story_id: 'story-123', title: 'Story' },
        message: 'Error message',
      });

      const request = new Request('http://localhost/api/stories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          epic_id: 'epic-1',
          title: 'Story',
        }),
      });

      const response = await POST({ request } as any);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
    });
  });

  describe('GET /api/stories/[id]', () => {
    it('should get story by ID successfully', async () => {
      const { GET } = await import('../stories/[id]');

      const mockResponse = {
        story_id: 'story-123',
        title: 'Story 1',
        brief: 'Brief',
        state: 'draft',
      };

      mockPromisifyGrpcCall.mockResolvedValue(mockResponse);

      const response = await GET({ params: { id: 'story-123' } } as any);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(data.story.story_id).toBe('story-123');
      expect(mockBuildGetStoryRequest).toHaveBeenCalledWith({ story_id: 'story-123' });
      expect(mockPromisifyGrpcCall).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          story_id: 'story-123',
        })
      );
    });

    it('should reject missing story_id', async () => {
      const { GET } = await import('../stories/[id]');

      const response = await GET({ params: {} } as any);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.message).toBe('story_id is required');
    });

    it('should handle story not found (no story_id in response)', async () => {
      const { GET } = await import('../stories/[id]');

      mockPromisifyGrpcCall.mockResolvedValue(null);

      const response = await GET({ params: { id: 'story-123' } } as any);
      const data = await response.json();

      expect(response.status).toBe(404);
      expect(data.success).toBe(false);
      expect(data.message).toBe('Story not found');
    });

    it('should handle gRPC ServiceError', async () => {
      const { GET } = await import('../stories/[id]');

      const error: grpc.ServiceError = {
        code: grpc.status.NOT_FOUND,
        message: 'Story not found',
        details: '',
        name: 'ServiceError',
      };

      mockPromisifyGrpcCall.mockRejectedValue(error);
      mockIsServiceError.mockReturnValue(true);
      mockGrpcErrorToHttpStatus.mockReturnValue(404);

      const response = await GET({ params: { id: 'story-123' } } as any);
      const data = await response.json();

      expect(response.status).toBe(404);
      expect(data.success).toBe(false);
      expect(data.message).toBe('Story not found');
    });
  });

  describe('POST /api/stories/[id]/transition', () => {
    it('should transition story successfully', async () => {
      const { POST } = await import('../stories/[id]/transition');

      const mockResponse = {
        story: {
          story_id: 'story-123',
          title: 'Story 1',
          state: 'in_progress',
        },
        success: true,
        message: 'Story transitioned',
      };

      mockPromisifyGrpcCall.mockResolvedValue(mockResponse);

      const request = new Request('http://localhost/api/stories/story-123/transition', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_state: 'in_progress',
          transitioned_by: 'user1',
        }),
      });

      const response = await POST({ params: { id: 'story-123' }, request } as any);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(data.story.state).toBe('in_progress');
      expect(mockBuildTransitionStoryRequest).toHaveBeenCalledWith(
        expect.objectContaining({
          story_id: 'story-123',
          target_state: 'in_progress',
          transitioned_by: 'user1',
        })
      );
      expect(mockPromisifyGrpcCall).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          story_id: 'story-123',
          target_state: 'in_progress',
          transitioned_by: 'user1',
        })
      );
    });

    it('should reject missing story_id', async () => {
      const { POST } = await import('../stories/[id]/transition');

      const request = new Request('http://localhost/api/stories/transition', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_state: 'in_progress',
        }),
      });

      const response = await POST({ params: {}, request } as any);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.message).toBe('story_id is required');
    });

    it('should reject missing target_state', async () => {
      const { POST } = await import('../stories/[id]/transition');

      const request = new Request('http://localhost/api/stories/story-123/transition', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          transitioned_by: 'user1',
        }),
      });

      const response = await POST({ params: { id: 'story-123' }, request } as any);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.message).toBe('target_state is required');
    });

    it('should use default transitioned_by', async () => {
      const { POST } = await import('../stories/[id]/transition');

      mockPromisifyGrpcCall.mockResolvedValue({
        story: { story_id: 'story-123', state: 'in_progress' },
        success: true,
      });

      const request = new Request('http://localhost/api/stories/story-123/transition', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_state: 'in_progress',
        }),
      });

      await POST({ params: { id: 'story-123' }, request } as any);

      expect(mockBuildTransitionStoryRequest).toHaveBeenCalledWith(
        expect.objectContaining({
          transitioned_by: 'ui-user',
        })
      );
      expect(mockPromisifyGrpcCall).toHaveBeenCalledWith(
        expect.any(Function),
        expect.objectContaining({
          transitioned_by: 'ui-user',
        })
      );
    });

    it('should handle gRPC ServiceError', async () => {
      const { POST } = await import('../stories/[id]/transition');

      const error: grpc.ServiceError = {
        code: grpc.status.INVALID_ARGUMENT,
        message: 'Invalid transition',
        details: '',
        name: 'ServiceError',
      };

      mockPromisifyGrpcCall.mockRejectedValue(error);
      mockIsServiceError.mockReturnValue(true);
      mockGrpcErrorToHttpStatus.mockReturnValue(400);

      const request = new Request('http://localhost/api/stories/story-123/transition', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_state: 'in_progress',
        }),
      });

      const response = await POST({ params: { id: 'story-123' }, request } as any);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.message).toBe('Invalid transition');
    });

    it('should handle failed transition (success=false)', async () => {
      const { POST } = await import('../stories/[id]/transition');

      mockPromisifyGrpcCall.mockResolvedValue({
        success: false,
        message: 'Failed to transition story',
      });

      const request = new Request('http://localhost/api/stories/story-123/transition', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_state: 'in_progress',
        }),
      });

      const response = await POST({ params: { id: 'story-123' }, request } as any);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.success).toBe(false);
      expect(data.message).toBe('Failed to transition story');
    });
  });
});

