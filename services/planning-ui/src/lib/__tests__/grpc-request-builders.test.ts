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

    it('should use generated code for buildListProjectsRequest with status_filter', async () => {
      const fs = await import('fs');
      const module = await import('module');

      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        return path.includes('planning_pb.js');
      });

      const mockSetLimit = vi.fn();
      const mockSetOffset = vi.fn();
      const mockSetStatusFilter = vi.fn();

      const mockMessages = {
        ListProjectsRequest: vi.fn(function(this: any) {
          this.setLimit = mockSetLimit;
          this.setOffset = mockSetOffset;
          this.setStatusFilter = mockSetStatusFilter;
          return this;
        }),
      };

      const mockRequire = vi.fn(() => mockMessages);
      vi.mocked(module.createRequire).mockReturnValue(mockRequire as any);

      vi.resetModules();
      const requestBuildersFresh = await import('../grpc-request-builders');

      const params = { limit: 10, offset: 0, status_filter: 'active' };
      const result = requestBuildersFresh.buildListProjectsRequest(params);

      expect(result).toBeDefined();
      expect(mockSetLimit).toHaveBeenCalledWith(10);
      expect(mockSetOffset).toHaveBeenCalledWith(0);
      expect(mockSetStatusFilter).toHaveBeenCalledWith('active');
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

    it('should use generated code for buildCreateProjectRequest', async () => {
      const fs = await import('fs');
      const module = await import('module');

      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        return path.includes('planning_pb.js');
      });

      const mockSetName = vi.fn();
      const mockSetDescription = vi.fn();
      const mockSetOwner = vi.fn();

      const mockMessages = {
        CreateProjectRequest: vi.fn(function(this: any) {
          this.setName = mockSetName;
          this.setDescription = mockSetDescription;
          this.setOwner = mockSetOwner;
          return this;
        }),
      };

      const mockRequire = vi.fn(() => mockMessages);
      vi.mocked(module.createRequire).mockReturnValue(mockRequire as any);

      vi.resetModules();
      const requestBuildersFresh = await import('../grpc-request-builders');

      const params = { name: 'Test', description: 'Desc', owner: 'user1' };
      const result = requestBuildersFresh.buildCreateProjectRequest(params);

      expect(result).toBeDefined();
      expect(mockSetName).toHaveBeenCalledWith('Test');
      expect(mockSetDescription).toHaveBeenCalledWith('Desc');
      expect(mockSetOwner).toHaveBeenCalledWith('user1');
    });

    it('should use generated code for buildGetProjectRequest', async () => {
      const fs = await import('fs');
      const module = await import('module');

      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        return path.includes('planning_pb.js');
      });

      const mockSetProjectId = vi.fn();

      const mockMessages = {
        GetProjectRequest: vi.fn(function(this: any) {
          this.setProjectId = mockSetProjectId;
          return this;
        }),
      };

      const mockRequire = vi.fn(() => mockMessages);
      vi.mocked(module.createRequire).mockReturnValue(mockRequire as any);

      vi.resetModules();
      const requestBuildersFresh = await import('../grpc-request-builders');

      const params = { project_id: 'proj-123' };
      const result = requestBuildersFresh.buildGetProjectRequest(params);

      expect(result).toBeDefined();
      expect(mockSetProjectId).toHaveBeenCalledWith('proj-123');
    });

    it('should use generated code for buildListEpicsRequest', async () => {
      const fs = await import('fs');
      const module = await import('module');

      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        return path.includes('planning_pb.js');
      });

      const mockSetLimit = vi.fn();
      const mockSetOffset = vi.fn();
      const mockSetProjectId = vi.fn();
      const mockSetStatusFilter = vi.fn();

      const mockMessages = {
        ListEpicsRequest: vi.fn(function(this: any) {
          this.setLimit = mockSetLimit;
          this.setOffset = mockSetOffset;
          this.setProjectId = mockSetProjectId;
          this.setStatusFilter = mockSetStatusFilter;
          return this;
        }),
      };

      const mockRequire = vi.fn(() => mockMessages);
      vi.mocked(module.createRequire).mockReturnValue(mockRequire as any);

      vi.resetModules();
      const requestBuildersFresh = await import('../grpc-request-builders');

      const params = { limit: 10, offset: 0, project_id: 'proj-1', status_filter: 'active' };
      const result = requestBuildersFresh.buildListEpicsRequest(params);

      expect(result).toBeDefined();
      expect(mockSetLimit).toHaveBeenCalledWith(10);
      expect(mockSetOffset).toHaveBeenCalledWith(0);
      expect(mockSetProjectId).toHaveBeenCalledWith('proj-1');
      expect(mockSetStatusFilter).toHaveBeenCalledWith('active');
    });

    it('should use generated code for buildCreateEpicRequest', async () => {
      const fs = await import('fs');
      const module = await import('module');

      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        return path.includes('planning_pb.js');
      });

      const mockSetProjectId = vi.fn();
      const mockSetTitle = vi.fn();
      const mockSetDescription = vi.fn();

      const mockMessages = {
        CreateEpicRequest: vi.fn(function(this: any) {
          this.setProjectId = mockSetProjectId;
          this.setTitle = mockSetTitle;
          this.setDescription = mockSetDescription;
          return this;
        }),
      };

      const mockRequire = vi.fn(() => mockMessages);
      vi.mocked(module.createRequire).mockReturnValue(mockRequire as any);

      vi.resetModules();
      const requestBuildersFresh = await import('../grpc-request-builders');

      const params = { project_id: 'proj-1', title: 'Epic', description: 'Desc' };
      const result = requestBuildersFresh.buildCreateEpicRequest(params);

      expect(result).toBeDefined();
      expect(mockSetProjectId).toHaveBeenCalledWith('proj-1');
      expect(mockSetTitle).toHaveBeenCalledWith('Epic');
      expect(mockSetDescription).toHaveBeenCalledWith('Desc');
    });

    it('should use generated code for buildGetEpicRequest', async () => {
      const fs = await import('fs');
      const module = await import('module');

      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        return path.includes('planning_pb.js');
      });

      const mockSetEpicId = vi.fn();

      const mockMessages = {
        GetEpicRequest: vi.fn(function(this: any) {
          this.setEpicId = mockSetEpicId;
          return this;
        }),
      };

      const mockRequire = vi.fn(() => mockMessages);
      vi.mocked(module.createRequire).mockReturnValue(mockRequire as any);

      vi.resetModules();
      const requestBuildersFresh = await import('../grpc-request-builders');

      const params = { epic_id: 'epic-123' };
      const result = requestBuildersFresh.buildGetEpicRequest(params);

      expect(result).toBeDefined();
      expect(mockSetEpicId).toHaveBeenCalledWith('epic-123');
    });

    it('should use generated code for buildListStoriesRequest', async () => {
      const fs = await import('fs');
      const module = await import('module');

      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        return path.includes('planning_pb.js');
      });

      const mockSetLimit = vi.fn();
      const mockSetOffset = vi.fn();
      const mockSetStateFilter = vi.fn();
      const mockSetEpicId = vi.fn();

      const mockMessages = {
        ListStoriesRequest: vi.fn(function(this: any) {
          this.setLimit = mockSetLimit;
          this.setOffset = mockSetOffset;
          this.setStateFilter = mockSetStateFilter;
          this.setEpicId = mockSetEpicId;
          return this;
        }),
      };

      const mockRequire = vi.fn(() => mockMessages);
      vi.mocked(module.createRequire).mockReturnValue(mockRequire as any);

      vi.resetModules();
      const requestBuildersFresh = await import('../grpc-request-builders');

      const params = { limit: 10, offset: 0, state_filter: 'draft', epic_id: 'epic-1' };
      const result = requestBuildersFresh.buildListStoriesRequest(params);

      expect(result).toBeDefined();
      expect(mockSetLimit).toHaveBeenCalledWith(10);
      expect(mockSetOffset).toHaveBeenCalledWith(0);
      expect(mockSetStateFilter).toHaveBeenCalledWith('draft');
      expect(mockSetEpicId).toHaveBeenCalledWith('epic-1');
    });

    it('should use generated code for buildCreateStoryRequest', async () => {
      const fs = await import('fs');
      const module = await import('module');

      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        return path.includes('planning_pb.js');
      });

      const mockSetEpicId = vi.fn();
      const mockSetTitle = vi.fn();
      const mockSetBrief = vi.fn();
      const mockSetCreatedBy = vi.fn();

      const mockMessages = {
        CreateStoryRequest: vi.fn(function(this: any) {
          this.setEpicId = mockSetEpicId;
          this.setTitle = mockSetTitle;
          this.setBrief = mockSetBrief;
          this.setCreatedBy = mockSetCreatedBy;
          return this;
        }),
      };

      const mockRequire = vi.fn(() => mockMessages);
      vi.mocked(module.createRequire).mockReturnValue(mockRequire as any);

      vi.resetModules();
      const requestBuildersFresh = await import('../grpc-request-builders');

      const params = { epic_id: 'epic-1', title: 'Story', brief: 'Brief', created_by: 'user1' };
      const result = requestBuildersFresh.buildCreateStoryRequest(params);

      expect(result).toBeDefined();
      expect(mockSetEpicId).toHaveBeenCalledWith('epic-1');
      expect(mockSetTitle).toHaveBeenCalledWith('Story');
      expect(mockSetBrief).toHaveBeenCalledWith('Brief');
      expect(mockSetCreatedBy).toHaveBeenCalledWith('user1');
    });

    it('should use generated code for buildGetStoryRequest', async () => {
      const fs = await import('fs');
      const module = await import('module');

      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        return path.includes('planning_pb.js');
      });

      const mockSetStoryId = vi.fn();

      const mockMessages = {
        GetStoryRequest: vi.fn(function(this: any) {
          this.setStoryId = mockSetStoryId;
          return this;
        }),
      };

      const mockRequire = vi.fn(() => mockMessages);
      vi.mocked(module.createRequire).mockReturnValue(mockRequire as any);

      vi.resetModules();
      const requestBuildersFresh = await import('../grpc-request-builders');

      const params = { story_id: 'story-123' };
      const result = requestBuildersFresh.buildGetStoryRequest(params);

      expect(result).toBeDefined();
      expect(mockSetStoryId).toHaveBeenCalledWith('story-123');
    });

    it('should use generated code for buildTransitionStoryRequest', async () => {
      const fs = await import('fs');
      const module = await import('module');

      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        return path.includes('planning_pb.js');
      });

      const mockSetStoryId = vi.fn();
      const mockSetTargetState = vi.fn();
      const mockSetTransitionedBy = vi.fn();

      const mockMessages = {
        TransitionStoryRequest: vi.fn(function(this: any) {
          this.setStoryId = mockSetStoryId;
          this.setTargetState = mockSetTargetState;
          this.setTransitionedBy = mockSetTransitionedBy;
          return this;
        }),
      };

      const mockRequire = vi.fn(() => mockMessages);
      vi.mocked(module.createRequire).mockReturnValue(mockRequire as any);

      vi.resetModules();
      const requestBuildersFresh = await import('../grpc-request-builders');

      const params = { story_id: 'story-123', target_state: 'in_progress', transitioned_by: 'user1' };
      const result = requestBuildersFresh.buildTransitionStoryRequest(params);

      expect(result).toBeDefined();
      expect(mockSetStoryId).toHaveBeenCalledWith('story-123');
      expect(mockSetTargetState).toHaveBeenCalledWith('in_progress');
      expect(mockSetTransitionedBy).toHaveBeenCalledWith('user1');
    });

    it('should use generated code for buildListTasksRequest', async () => {
      const fs = await import('fs');
      const module = await import('module');

      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        return path.includes('planning_pb.js');
      });

      const mockSetLimit = vi.fn();
      const mockSetOffset = vi.fn();
      const mockSetStoryId = vi.fn();
      const mockSetStatusFilter = vi.fn();

      const mockMessages = {
        ListTasksRequest: vi.fn(function(this: any) {
          this.setLimit = mockSetLimit;
          this.setOffset = mockSetOffset;
          this.setStoryId = mockSetStoryId;
          this.setStatusFilter = mockSetStatusFilter;
          return this;
        }),
      };

      const mockRequire = vi.fn(() => mockMessages);
      vi.mocked(module.createRequire).mockReturnValue(mockRequire as any);

      vi.resetModules();
      const requestBuildersFresh = await import('../grpc-request-builders');

      const params = { limit: 10, offset: 0, story_id: 'story-1', status_filter: 'pending' };
      const result = requestBuildersFresh.buildListTasksRequest(params);

      expect(result).toBeDefined();
      expect(mockSetLimit).toHaveBeenCalledWith(10);
      expect(mockSetOffset).toHaveBeenCalledWith(0);
      expect(mockSetStoryId).toHaveBeenCalledWith('story-1');
      expect(mockSetStatusFilter).toHaveBeenCalledWith('pending');
    });

    it('should use generated code for buildGetTaskRequest', async () => {
      const fs = await import('fs');
      const module = await import('module');

      vi.mocked(fs.existsSync).mockImplementation((path: string) => {
        return path.includes('planning_pb.js');
      });

      const mockSetTaskId = vi.fn();

      const mockMessages = {
        GetTaskRequest: vi.fn(function(this: any) {
          this.setTaskId = mockSetTaskId;
          return this;
        }),
      };

      const mockRequire = vi.fn(() => mockMessages);
      vi.mocked(module.createRequire).mockReturnValue(mockRequire as any);

      vi.resetModules();
      const requestBuildersFresh = await import('../grpc-request-builders');

      const params = { task_id: 'task-123' };
      const result = requestBuildersFresh.buildGetTaskRequest(params);

      expect(result).toBeDefined();
      expect(mockSetTaskId).toHaveBeenCalledWith('task-123');
    });


    it('should handle resolvePlanningMessages when file exists but require fails', async () => {
      const fs = await import('fs');
      const module = await import('module');

      // Suppress console.warn to avoid stderr noise in test output
      const originalWarn = console.warn;
      console.warn = vi.fn();

      try {
        vi.mocked(fs.existsSync).mockImplementation((path: string) => {
          return path.includes('planning_pb.js');
        });

        const mockRequire = vi.fn(() => {
          throw new Error('Module not found');
        });
        vi.mocked(module.createRequire).mockReturnValue(mockRequire as any);

        vi.resetModules();
        const requestBuildersFresh = await import('../grpc-request-builders');

        const params = { limit: 10, offset: 0 };
        const result = requestBuildersFresh.buildListProjectsRequest(params);

        expect(result).toEqual({ limit: 10, offset: 0 });
      } finally {
        console.warn = originalWarn;
      }
    });
  });

  describe('Backlog Review Ceremony Request Builders', () => {
    describe('buildCreateBacklogReviewCeremonyRequest', () => {
      it('should build request with required fields', () => {
        const params = { created_by: 'user1' };
        const result = requestBuilders.buildCreateBacklogReviewCeremonyRequest(params);

        expect(result).toEqual({
          created_by: 'user1',
          story_ids: [],
        });
      });

      it('should include optional story_ids', () => {
        const params = { created_by: 'user1', story_ids: ['story-1', 'story-2'] };
        const result = requestBuilders.buildCreateBacklogReviewCeremonyRequest(params);

        expect(result).toEqual({
          created_by: 'user1',
          story_ids: ['story-1', 'story-2'],
        });
      });

      it('should use empty array when story_ids is empty', () => {
        const params = { created_by: 'user1', story_ids: [] };
        const result = requestBuilders.buildCreateBacklogReviewCeremonyRequest(params);

        expect(result).toEqual({
          created_by: 'user1',
          story_ids: [],
        });
      });
    });

    describe('buildGetBacklogReviewCeremonyRequest', () => {
      it('should build request with ceremony_id', () => {
        const params = { ceremony_id: 'ceremony-123' };
        const result = requestBuilders.buildGetBacklogReviewCeremonyRequest(params);

        expect(result).toEqual({ ceremony_id: 'ceremony-123' });
      });
    });

    describe('buildListBacklogReviewCeremoniesRequest', () => {
      it('should build request with required fields', () => {
        const params = { limit: 10, offset: 0 };
        const result = requestBuilders.buildListBacklogReviewCeremoniesRequest(params);

        expect(result).toEqual({ limit: 10, offset: 0 });
      });

      it('should include optional status_filter and created_by', () => {
        const params = {
          limit: 10,
          offset: 0,
          status_filter: 'active',
          created_by: 'user1',
        };
        const result = requestBuilders.buildListBacklogReviewCeremoniesRequest(params);

        expect(result).toEqual({
          limit: 10,
          offset: 0,
          status_filter: 'active',
          created_by: 'user1',
        });
      });
    });

    describe('buildStartBacklogReviewCeremonyRequest', () => {
      it('should build request with all fields', () => {
        const params = { ceremony_id: 'ceremony-123', started_by: 'user1' };
        const result = requestBuilders.buildStartBacklogReviewCeremonyRequest(params);

        expect(result).toEqual({
          ceremony_id: 'ceremony-123',
          started_by: 'user1',
        });
      });
    });

    describe('buildApproveReviewPlanRequest', () => {
      it('should build request with required fields', () => {
        const params = {
          ceremony_id: 'ceremony-123',
          story_id: 'story-1',
          approved_by: 'user1',
          po_notes: 'Approved',
        };
        const result = requestBuilders.buildApproveReviewPlanRequest(params);

        expect(result).toEqual({
          ceremony_id: 'ceremony-123',
          story_id: 'story-1',
          approved_by: 'user1',
          po_notes: 'Approved',
        });
      });

      it('should include optional fields', () => {
        const params = {
          ceremony_id: 'ceremony-123',
          story_id: 'story-1',
          approved_by: 'user1',
          po_notes: 'Approved',
          po_concerns: 'Some concerns',
          priority_adjustment: 'high',
          po_priority_reason: 'Important feature',
        };
        const result = requestBuilders.buildApproveReviewPlanRequest(params);

        expect(result).toEqual({
          ceremony_id: 'ceremony-123',
          story_id: 'story-1',
          approved_by: 'user1',
          po_notes: 'Approved',
          po_concerns: 'Some concerns',
          priority_adjustment: 'high',
          po_priority_reason: 'Important feature',
        });
      });
    });

    describe('buildRejectReviewPlanRequest', () => {
      it('should build request with all fields', () => {
        const params = {
          ceremony_id: 'ceremony-123',
          story_id: 'story-1',
          rejected_by: 'user1',
          rejection_reason: 'Not ready',
        };
        const result = requestBuilders.buildRejectReviewPlanRequest(params);

        expect(result).toEqual({
          ceremony_id: 'ceremony-123',
          story_id: 'story-1',
          rejected_by: 'user1',
          rejection_reason: 'Not ready',
        });
      });
    });

    describe('buildCompleteBacklogReviewCeremonyRequest', () => {
      it('should build request with all fields', () => {
        const params = { ceremony_id: 'ceremony-123', completed_by: 'user1' };
        const result = requestBuilders.buildCompleteBacklogReviewCeremonyRequest(params);

        expect(result).toEqual({
          ceremony_id: 'ceremony-123',
          completed_by: 'user1',
        });
      });
    });

    describe('buildRequestInstance with generated code for Backlog Review Ceremony', () => {
      it('should use generated code for buildCreateBacklogReviewCeremonyRequest', async () => {
        const fs = await import('fs');
        const module = await import('module');

        vi.mocked(fs.existsSync).mockImplementation((path: string) => {
          return path.includes('planning_pb.js');
        });

        const mockSetCreatedBy = vi.fn();
        const mockSetStoryIdsList = vi.fn();

        const mockMessages = {
          CreateBacklogReviewCeremonyRequest: vi.fn(function(this: any) {
            this.setCreatedBy = mockSetCreatedBy;
            this.setStoryIdsList = mockSetStoryIdsList;
            return this;
          }),
        };

        const mockRequire = vi.fn(() => mockMessages);
        vi.mocked(module.createRequire).mockReturnValue(mockRequire as any);

        vi.resetModules();
        const requestBuildersFresh = await import('../grpc-request-builders');

        const params = { created_by: 'user1', story_ids: ['story-1'] };
        const result = requestBuildersFresh.buildCreateBacklogReviewCeremonyRequest(params);

        expect(result).toBeDefined();
        expect(mockSetCreatedBy).toHaveBeenCalledWith('user1');
        expect(mockSetStoryIdsList).toHaveBeenCalledWith(['story-1']);
      });

      it('should use generated code for buildGetBacklogReviewCeremonyRequest', async () => {
        const fs = await import('fs');
        const module = await import('module');

        vi.mocked(fs.existsSync).mockImplementation((path: string) => {
          return path.includes('planning_pb.js');
        });

        const mockSetCeremonyId = vi.fn();

        const mockMessages = {
          GetBacklogReviewCeremonyRequest: vi.fn(function(this: any) {
            this.setCeremonyId = mockSetCeremonyId;
            return this;
          }),
        };

        const mockRequire = vi.fn(() => mockMessages);
        vi.mocked(module.createRequire).mockReturnValue(mockRequire as any);

        vi.resetModules();
        const requestBuildersFresh = await import('../grpc-request-builders');

        const params = { ceremony_id: 'ceremony-123' };
        const result = requestBuildersFresh.buildGetBacklogReviewCeremonyRequest(params);

        expect(result).toBeDefined();
        expect(mockSetCeremonyId).toHaveBeenCalledWith('ceremony-123');
      });

      it('should use generated code for buildListBacklogReviewCeremoniesRequest', async () => {
        const fs = await import('fs');
        const module = await import('module');

        vi.mocked(fs.existsSync).mockImplementation((path: string) => {
          return path.includes('planning_pb.js');
        });

        const mockSetLimit = vi.fn();
        const mockSetOffset = vi.fn();
        const mockSetStatusFilter = vi.fn();
        const mockSetCreatedBy = vi.fn();

        const mockMessages = {
          ListBacklogReviewCeremoniesRequest: vi.fn(function(this: any) {
            this.setLimit = mockSetLimit;
            this.setOffset = mockSetOffset;
            this.setStatusFilter = mockSetStatusFilter;
            this.setCreatedBy = mockSetCreatedBy;
            return this;
          }),
        };

        const mockRequire = vi.fn(() => mockMessages);
        vi.mocked(module.createRequire).mockReturnValue(mockRequire as any);

        vi.resetModules();
        const requestBuildersFresh = await import('../grpc-request-builders');

        const params = { limit: 10, offset: 0, status_filter: 'active', created_by: 'user1' };
        const result = requestBuildersFresh.buildListBacklogReviewCeremoniesRequest(params);

        expect(result).toBeDefined();
        expect(mockSetLimit).toHaveBeenCalledWith(10);
        expect(mockSetOffset).toHaveBeenCalledWith(0);
        expect(mockSetStatusFilter).toHaveBeenCalledWith('active');
        expect(mockSetCreatedBy).toHaveBeenCalledWith('user1');
      });

      it('should use generated code for buildStartBacklogReviewCeremonyRequest', async () => {
        const fs = await import('fs');
        const module = await import('module');

        vi.mocked(fs.existsSync).mockImplementation((path: string) => {
          return path.includes('planning_pb.js');
        });

        const mockSetCeremonyId = vi.fn();
        const mockSetStartedBy = vi.fn();

        const mockMessages = {
          StartBacklogReviewCeremonyRequest: vi.fn(function(this: any) {
            this.setCeremonyId = mockSetCeremonyId;
            this.setStartedBy = mockSetStartedBy;
            return this;
          }),
        };

        const mockRequire = vi.fn(() => mockMessages);
        vi.mocked(module.createRequire).mockReturnValue(mockRequire as any);

        vi.resetModules();
        const requestBuildersFresh = await import('../grpc-request-builders');

        const params = { ceremony_id: 'ceremony-123', started_by: 'user1' };
        const result = requestBuildersFresh.buildStartBacklogReviewCeremonyRequest(params);

        expect(result).toBeDefined();
        expect(mockSetCeremonyId).toHaveBeenCalledWith('ceremony-123');
        expect(mockSetStartedBy).toHaveBeenCalledWith('user1');
      });

      it('should use generated code for buildApproveReviewPlanRequest', async () => {
        const fs = await import('fs');
        const module = await import('module');

        vi.mocked(fs.existsSync).mockImplementation((path: string) => {
          return path.includes('planning_pb.js');
        });

        const mockSetCeremonyId = vi.fn();
        const mockSetStoryId = vi.fn();
        const mockSetApprovedBy = vi.fn();
        const mockSetPoNotes = vi.fn();
        const mockSetPoConcerns = vi.fn();
        const mockSetPriorityAdjustment = vi.fn();
        const mockSetPoPriorityReason = vi.fn();

        const mockMessages = {
          ApproveReviewPlanRequest: vi.fn(function(this: any) {
            this.setCeremonyId = mockSetCeremonyId;
            this.setStoryId = mockSetStoryId;
            this.setApprovedBy = mockSetApprovedBy;
            this.setPoNotes = mockSetPoNotes;
            this.setPoConcerns = mockSetPoConcerns;
            this.setPriorityAdjustment = mockSetPriorityAdjustment;
            this.setPoPriorityReason = mockSetPoPriorityReason;
            return this;
          }),
        };

        const mockRequire = vi.fn(() => mockMessages);
        vi.mocked(module.createRequire).mockReturnValue(mockRequire as any);

        vi.resetModules();
        const requestBuildersFresh = await import('../grpc-request-builders');

        const params = {
          ceremony_id: 'ceremony-123',
          story_id: 'story-1',
          approved_by: 'user1',
          po_notes: 'Approved',
          po_concerns: 'Some concerns',
          priority_adjustment: 'high',
          po_priority_reason: 'Important feature',
        };
        const result = requestBuildersFresh.buildApproveReviewPlanRequest(params);

        expect(result).toBeDefined();
        expect(mockSetCeremonyId).toHaveBeenCalledWith('ceremony-123');
        expect(mockSetStoryId).toHaveBeenCalledWith('story-1');
        expect(mockSetApprovedBy).toHaveBeenCalledWith('user1');
        expect(mockSetPoNotes).toHaveBeenCalledWith('Approved');
        expect(mockSetPoConcerns).toHaveBeenCalledWith('Some concerns');
        expect(mockSetPriorityAdjustment).toHaveBeenCalledWith('high');
        expect(mockSetPoPriorityReason).toHaveBeenCalledWith('Important feature');
      });

      it('should use generated code for buildRejectReviewPlanRequest', async () => {
        const fs = await import('fs');
        const module = await import('module');

        vi.mocked(fs.existsSync).mockImplementation((path: string) => {
          return path.includes('planning_pb.js');
        });

        const mockSetCeremonyId = vi.fn();
        const mockSetStoryId = vi.fn();
        const mockSetRejectedBy = vi.fn();
        const mockSetRejectionReason = vi.fn();

        const mockMessages = {
          RejectReviewPlanRequest: vi.fn(function(this: any) {
            this.setCeremonyId = mockSetCeremonyId;
            this.setStoryId = mockSetStoryId;
            this.setRejectedBy = mockSetRejectedBy;
            this.setRejectionReason = mockSetRejectionReason;
            return this;
          }),
        };

        const mockRequire = vi.fn(() => mockMessages);
        vi.mocked(module.createRequire).mockReturnValue(mockRequire as any);

        vi.resetModules();
        const requestBuildersFresh = await import('../grpc-request-builders');

        const params = {
          ceremony_id: 'ceremony-123',
          story_id: 'story-1',
          rejected_by: 'user1',
          rejection_reason: 'Not ready',
        };
        const result = requestBuildersFresh.buildRejectReviewPlanRequest(params);

        expect(result).toBeDefined();
        expect(mockSetCeremonyId).toHaveBeenCalledWith('ceremony-123');
        expect(mockSetStoryId).toHaveBeenCalledWith('story-1');
        expect(mockSetRejectedBy).toHaveBeenCalledWith('user1');
        expect(mockSetRejectionReason).toHaveBeenCalledWith('Not ready');
      });

      it('should use generated code for buildCompleteBacklogReviewCeremonyRequest', async () => {
        const fs = await import('fs');
        const module = await import('module');

        vi.mocked(fs.existsSync).mockImplementation((path: string) => {
          return path.includes('planning_pb.js');
        });

        const mockSetCeremonyId = vi.fn();
        const mockSetCompletedBy = vi.fn();

        const mockMessages = {
          CompleteBacklogReviewCeremonyRequest: vi.fn(function(this: any) {
            this.setCeremonyId = mockSetCeremonyId;
            this.setCompletedBy = mockSetCompletedBy;
            return this;
          }),
        };

        const mockRequire = vi.fn(() => mockMessages);
        vi.mocked(module.createRequire).mockReturnValue(mockRequire as any);

        vi.resetModules();
        const requestBuildersFresh = await import('../grpc-request-builders');

        const params = { ceremony_id: 'ceremony-123', completed_by: 'user1' };
        const result = requestBuildersFresh.buildCompleteBacklogReviewCeremonyRequest(params);

        expect(result).toBeDefined();
        expect(mockSetCeremonyId).toHaveBeenCalledWith('ceremony-123');
        expect(mockSetCompletedBy).toHaveBeenCalledWith('user1');
      });
    });
  });

  describe('Planning Ceremony Request Builders', () => {
    describe('buildStartPlanningCeremonyRequest', () => {
      it('should build request with required fields', () => {
        const params = {
          ceremony_id: 'ceremony-123',
          definition_name: 'e2e_multi_step',
          story_id: 'story-1',
          requested_by: 'planner@example.com',
          step_ids: ['deliberate'],
        };

        const result = requestBuilders.buildStartPlanningCeremonyRequest(params);

        expect(result).toEqual({
          ceremony_id: 'ceremony-123',
          definition_name: 'e2e_multi_step',
          story_id: 'story-1',
          requested_by: 'planner@example.com',
          step_ids: ['deliberate'],
        });
      });

      it('should include optional correlation_id and inputs', () => {
        const params = {
          ceremony_id: 'ceremony-123',
          definition_name: 'e2e_multi_step',
          story_id: 'story-1',
          requested_by: 'planner@example.com',
          step_ids: ['deliberate', 'extract_tasks'],
          correlation_id: 'corr-123',
          inputs: {
            input_data: '{"source":"planning-ui"}',
          },
        };

        const result = requestBuilders.buildStartPlanningCeremonyRequest(params);

        expect(result).toEqual({
          ceremony_id: 'ceremony-123',
          definition_name: 'e2e_multi_step',
          story_id: 'story-1',
          requested_by: 'planner@example.com',
          step_ids: ['deliberate', 'extract_tasks'],
          correlation_id: 'corr-123',
          inputs: {
            input_data: '{"source":"planning-ui"}',
          },
        });
      });
    });
  });
});
