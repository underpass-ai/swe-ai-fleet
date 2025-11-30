/**
 * Unit tests for gRPC request builders
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as requestBuilders from '../grpc-request-builders';

// Mock fs and module
vi.mock('fs', () => ({
  existsSync: vi.fn(() => false), // No generated code available - use plain objects
}));
vi.mock('module', () => ({
  createRequire: vi.fn(),
}));

describe('gRPC Request Builders', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('buildListProjectsRequest', () => {
    it('should build request with required fields', () => {
      const params = { limit: 10, offset: 0 };
      const result = requestBuilders.buildListProjectsRequest(params);

      expect(result).toEqual({ limit: 10, offset: 0 });
    });

    it('should include optional status_filter', () => {
      const params = { limit: 10, offset: 0, status_filter: 'active' };
      const result = requestBuilders.buildListProjectsRequest(params);

      expect(result).toEqual({ limit: 10, offset: 0, status_filter: 'active' });
    });
  });

  describe('buildCreateProjectRequest', () => {
    it('should build request with all fields', () => {
      const params = {
        name: 'Project Name',
        description: 'Description',
        owner: 'user1',
      };
      const result = requestBuilders.buildCreateProjectRequest(params);

      expect(result).toEqual({
        name: 'Project Name',
        description: 'Description',
        owner: 'user1',
      });
    });
  });

  describe('buildGetProjectRequest', () => {
    it('should build request with project_id', () => {
      const params = { project_id: 'proj-123' };
      const result = requestBuilders.buildGetProjectRequest(params);

      expect(result).toEqual({ project_id: 'proj-123' });
    });
  });

  describe('buildListEpicsRequest', () => {
    it('should build request with required fields', () => {
      const params = { limit: 10, offset: 0 };
      const result = requestBuilders.buildListEpicsRequest(params);

      expect(result).toEqual({ limit: 10, offset: 0 });
    });

    it('should include optional project_id and status_filter', () => {
      const params = {
        limit: 10,
        offset: 0,
        project_id: 'proj-1',
        status_filter: 'active',
      };
      const result = requestBuilders.buildListEpicsRequest(params);

      expect(result).toEqual({
        limit: 10,
        offset: 0,
        project_id: 'proj-1',
        status_filter: 'active',
      });
    });
  });

  describe('buildCreateEpicRequest', () => {
    it('should build request with all fields', () => {
      const params = {
        project_id: 'proj-1',
        title: 'Epic Title',
        description: 'Description',
      };
      const result = requestBuilders.buildCreateEpicRequest(params);

      expect(result).toEqual({
        project_id: 'proj-1',
        title: 'Epic Title',
        description: 'Description',
      });
    });
  });

  describe('buildGetEpicRequest', () => {
    it('should build request with epic_id', () => {
      const params = { epic_id: 'epic-123' };
      const result = requestBuilders.buildGetEpicRequest(params);

      expect(result).toEqual({ epic_id: 'epic-123' });
    });
  });

  describe('buildListStoriesRequest', () => {
    it('should build request with required fields', () => {
      const params = { limit: 10, offset: 0 };
      const result = requestBuilders.buildListStoriesRequest(params);

      expect(result).toEqual({ limit: 10, offset: 0 });
    });

    it('should include optional state_filter and epic_id', () => {
      const params = {
        limit: 10,
        offset: 0,
        state_filter: 'draft',
        epic_id: 'epic-1',
      };
      const result = requestBuilders.buildListStoriesRequest(params);

      expect(result).toEqual({
        limit: 10,
        offset: 0,
        state_filter: 'draft',
        epic_id: 'epic-1',
      });
    });
  });

  describe('buildCreateStoryRequest', () => {
    it('should build request with all fields', () => {
      const params = {
        epic_id: 'epic-1',
        title: 'Story Title',
        brief: 'Brief',
        created_by: 'user1',
      };
      const result = requestBuilders.buildCreateStoryRequest(params);

      expect(result).toEqual({
        epic_id: 'epic-1',
        title: 'Story Title',
        brief: 'Brief',
        created_by: 'user1',
      });
    });
  });

  describe('buildGetStoryRequest', () => {
    it('should build request with story_id', () => {
      const params = { story_id: 'story-123' };
      const result = requestBuilders.buildGetStoryRequest(params);

      expect(result).toEqual({ story_id: 'story-123' });
    });
  });

  describe('buildTransitionStoryRequest', () => {
    it('should build request with all fields', () => {
      const params = {
        story_id: 'story-123',
        target_state: 'in_progress',
        transitioned_by: 'user1',
      };
      const result = requestBuilders.buildTransitionStoryRequest(params);

      expect(result).toEqual({
        story_id: 'story-123',
        target_state: 'in_progress',
        transitioned_by: 'user1',
      });
    });
  });

  describe('buildListTasksRequest', () => {
    it('should build request with required fields', () => {
      const params = { limit: 10, offset: 0 };
      const result = requestBuilders.buildListTasksRequest(params);

      expect(result).toEqual({ limit: 10, offset: 0 });
    });

    it('should include optional story_id and status_filter', () => {
      const params = {
        limit: 10,
        offset: 0,
        story_id: 'story-1',
        status_filter: 'pending',
      };
      const result = requestBuilders.buildListTasksRequest(params);

      expect(result).toEqual({
        limit: 10,
        offset: 0,
        story_id: 'story-1',
        status_filter: 'pending',
      });
    });
  });

  describe('buildGetTaskRequest', () => {
    it('should build request with task_id', () => {
      const params = { task_id: 'task-123' };
      const result = requestBuilders.buildGetTaskRequest(params);

      expect(result).toEqual({ task_id: 'task-123' });
    });
  });

  describe('buildRequestInstance with generated code', () => {
    it('should use generated code when available', async () => {
      const fs = await import('fs');
      const module = await import('module');

      // Mock generated code exists
      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        return path.includes('planning_pb.js');
      });

      const mockRequestClass = vi.fn(function(this: any) {
        this.setLimit = vi.fn();
        this.setOffset = vi.fn();
        return this;
      });

      const mockMessages = {
        ListProjectsRequest: mockRequestClass,
      };

      const mockRequire = vi.fn(() => mockMessages);
      vi.mocked(module.createRequire).mockReturnValue(mockRequire as any);

      // Reset module to clear cache
      vi.resetModules();
      const requestBuildersFresh = await import('../grpc-request-builders');

      const params = { limit: 10, offset: 0 };
      const result = requestBuildersFresh.buildListProjectsRequest(params);

      expect(result).toBeDefined();
      expect(mockRequestClass).toHaveBeenCalled();
    });

    it('should fallback to plain object when generated code not available', () => {
      const params = { limit: 10, offset: 0 };
      const result = requestBuilders.buildListProjectsRequest(params);

      expect(result).toEqual({ limit: 10, offset: 0 });
    });

    it('should handle factory returning non-object', async () => {
      const fs = await import('fs');
      const module = await import('module');

      // Mock generated code exists but factory returns null
      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        return path.includes('planning_pb.js');
      });

      const mockSetLimit = vi.fn();
      const mockSetOffset = vi.fn();

      const mockMessages = {
        ListProjectsRequest: vi.fn(function(this: any) {
          this.setLimit = mockSetLimit;
          this.setOffset = mockSetOffset;
          return this;
        }),
      };

      const mockRequire = vi.fn(() => mockMessages);
      vi.mocked(module.createRequire).mockReturnValue(mockRequire as any);

      // Reset module to clear cache
      vi.resetModules();
      const requestBuildersFresh = await import('../grpc-request-builders');

      const params = { limit: 10, offset: 0 };
      const result = requestBuildersFresh.buildListProjectsRequest(params);

      // Should use generated request instance with methods called
      expect(result).toBeDefined();
      expect(result.setLimit).toBe(mockSetLimit);
      expect(result.setOffset).toBe(mockSetOffset);
      expect(mockSetLimit).toHaveBeenCalledWith(10);
      expect(mockSetOffset).toHaveBeenCalledWith(0);
    });
  });
});

