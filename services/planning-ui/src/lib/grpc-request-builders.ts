import { existsSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';

/**
 * Helper module that builds typed gRPC request messages when the generated
 * protobuf classes are available. It falls back to plain objects so our
 * proto-loader based development flow keeps working.
 */

type PlanningMessagesModule = Record<string, any>;

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const require = createRequire(import.meta.url);

let planningMessages: PlanningMessagesModule | null | undefined;

function resolvePlanningMessages(): PlanningMessagesModule | null {
  if (planningMessages !== undefined) {
    return planningMessages;
  }

  const possiblePaths = [
    join(process.cwd(), 'gen/fleet/planning/v2/planning_pb.js'),
    join(__dirname, '../../../gen/fleet/planning/v2/planning_pb.js'),
    join(__dirname, '../../../../gen/fleet/planning/v2/planning_pb.js'),
    '/app/gen/fleet/planning/v2/planning_pb.js',
  ];

  for (const path of possiblePaths) {
    if (existsSync(path)) {
      try {
        planningMessages = require(path);
        return planningMessages;
      } catch (error) {
        console.warn(`Failed to load planning_pb from ${path}:`, error);
      }
    }
  }

  planningMessages = null;
  return planningMessages;
}

function buildRequestInstance<TParams>(
  factory: (messages: PlanningMessagesModule) => any,
  plainPayload: Record<string, unknown>
): any {
  const messages = resolvePlanningMessages();

  if (!messages) {
    return plainPayload;
  }

  const request = factory(messages);
  return typeof request === 'object' && request !== null ? request : plainPayload;
}

export interface ListProjectsParams {
  limit: number;
  offset: number;
  status_filter?: string;
}

export function buildListProjectsRequest(params: ListProjectsParams): any {
  const payload: Record<string, unknown> = {
    limit: params.limit,
    offset: params.offset,
  };

  if (params.status_filter) {
    payload.status_filter = params.status_filter;
  }

  return buildRequestInstance(
    (messages) => {
      const request = new messages.ListProjectsRequest();
      request.setLimit(params.limit);
      request.setOffset(params.offset);
      if (params.status_filter) {
        request.setStatusFilter(params.status_filter);
      }
      return request;
    },
    payload
  );
}

export interface CreateProjectParams {
  name: string;
  description: string;
  owner: string;
}

export function buildCreateProjectRequest(params: CreateProjectParams): any {
  const payload: Record<string, unknown> = {
    name: params.name,
    description: params.description,
    owner: params.owner,
  };

  return buildRequestInstance(
    (messages) => {
      const request = new messages.CreateProjectRequest();
      request.setName(params.name);
      request.setDescription(params.description);
      request.setOwner(params.owner);
      return request;
    },
    payload
  );
}

export interface GetProjectParams {
  project_id: string;
}

export function buildGetProjectRequest(params: GetProjectParams): any {
  const payload = { project_id: params.project_id };

  return buildRequestInstance(
    (messages) => {
      const request = new messages.GetProjectRequest();
      request.setProjectId(params.project_id);
      return request;
    },
    payload
  );
}

export interface ListEpicsParams {
  limit: number;
  offset: number;
  project_id?: string;
  status_filter?: string;
}

export function buildListEpicsRequest(params: ListEpicsParams): any {
  const payload: Record<string, unknown> = {
    limit: params.limit,
    offset: params.offset,
  };

  if (params.project_id) {
    payload.project_id = params.project_id;
  }

  if (params.status_filter) {
    payload.status_filter = params.status_filter;
  }

  return buildRequestInstance(
    (messages) => {
      const request = new messages.ListEpicsRequest();
      request.setLimit(params.limit);
      request.setOffset(params.offset);
      if (params.project_id) {
        request.setProjectId(params.project_id);
      }
      if (params.status_filter) {
        request.setStatusFilter(params.status_filter);
      }
      return request;
    },
    payload
  );
}

export interface CreateEpicParams {
  project_id: string;
  title: string;
  description: string;
}

export function buildCreateEpicRequest(params: CreateEpicParams): any {
  const payload: Record<string, unknown> = {
    project_id: params.project_id,
    title: params.title,
    description: params.description,
  };

  return buildRequestInstance(
    (messages) => {
      const request = new messages.CreateEpicRequest();
      request.setProjectId(params.project_id);
      request.setTitle(params.title);
      request.setDescription(params.description);
      return request;
    },
    payload
  );
}

export interface GetEpicParams {
  epic_id: string;
}

export function buildGetEpicRequest(params: GetEpicParams): any {
  const payload = { epic_id: params.epic_id };

  return buildRequestInstance(
    (messages) => {
      const request = new messages.GetEpicRequest();
      request.setEpicId(params.epic_id);
      return request;
    },
    payload
  );
}

export interface ListStoriesParams {
  limit: number;
  offset: number;
  state_filter?: string;
  epic_id?: string;
}

export function buildListStoriesRequest(params: ListStoriesParams): any {
  const payload: Record<string, unknown> = {
    limit: params.limit,
    offset: params.offset,
  };

  if (params.state_filter) {
    payload.state_filter = params.state_filter;
  }

  if (params.epic_id) {
    payload.epic_id = params.epic_id;
  }

  return buildRequestInstance(
    (messages) => {
      const request = new messages.ListStoriesRequest();
      request.setLimit(params.limit);
      request.setOffset(params.offset);
      if (params.state_filter) {
        request.setStateFilter(params.state_filter);
      }
      if (params.epic_id) {
        request.setEpicId(params.epic_id);
      }
      return request;
    },
    payload
  );
}

export interface CreateStoryParams {
  epic_id: string;
  title: string;
  brief: string;
  created_by: string;
}

export function buildCreateStoryRequest(params: CreateStoryParams): any {
  const payload: Record<string, unknown> = {
    epic_id: params.epic_id,
    title: params.title,
    brief: params.brief,
    created_by: params.created_by,
  };

  return buildRequestInstance(
    (messages) => {
      const request = new messages.CreateStoryRequest();
      request.setEpicId(params.epic_id);
      request.setTitle(params.title);
      request.setBrief(params.brief);
      request.setCreatedBy(params.created_by);
      return request;
    },
    payload
  );
}

export interface GetStoryParams {
  story_id: string;
}

export function buildGetStoryRequest(params: GetStoryParams): any {
  const payload = { story_id: params.story_id };

  return buildRequestInstance(
    (messages) => {
      const request = new messages.GetStoryRequest();
      request.setStoryId(params.story_id);
      return request;
    },
    payload
  );
}

export interface TransitionStoryParams {
  story_id: string;
  target_state: string;
  transitioned_by: string;
}

export function buildTransitionStoryRequest(params: TransitionStoryParams): any {
  const payload: Record<string, unknown> = {
    story_id: params.story_id,
    target_state: params.target_state,
    transitioned_by: params.transitioned_by,
  };

  return buildRequestInstance(
    (messages) => {
      const request = new messages.TransitionStoryRequest();
      request.setStoryId(params.story_id);
      request.setTargetState(params.target_state);
      request.setTransitionedBy(params.transitioned_by);
      return request;
    },
    payload
  );
}

export interface ListTasksParams {
  limit: number;
  offset: number;
  story_id?: string;
  status_filter?: string;
}

export function buildListTasksRequest(params: ListTasksParams): any {
  const payload: Record<string, unknown> = {
    limit: params.limit,
    offset: params.offset,
  };

  if (params.story_id) {
    payload.story_id = params.story_id;
  }

  if (params.status_filter) {
    payload.status_filter = params.status_filter;
  }

  return buildRequestInstance(
    (messages) => {
      const request = new messages.ListTasksRequest();
      request.setLimit(params.limit);
      request.setOffset(params.offset);
      if (params.story_id) {
        request.setStoryId(params.story_id);
      }
      if (params.status_filter) {
        request.setStatusFilter(params.status_filter);
      }
      return request;
    },
    payload
  );
}
