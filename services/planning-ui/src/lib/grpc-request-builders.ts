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

export interface GetTaskParams {
  task_id: string;
}

export function buildGetTaskRequest(params: GetTaskParams): any {
  const payload = { task_id: params.task_id };

  return buildRequestInstance(
    (messages) => {
      const request = new messages.GetTaskRequest();
      request.setTaskId(params.task_id);
      return request;
    },
    payload
  );
}

// ============================================================================
// BACKLOG REVIEW CEREMONY REQUEST BUILDERS
// ============================================================================

export interface CreateBacklogReviewCeremonyParams {
  created_by: string;
  story_ids?: string[];
}

export function buildCreateBacklogReviewCeremonyRequest(params: CreateBacklogReviewCeremonyParams): any {
  const payload: Record<string, unknown> = {
    created_by: params.created_by,
    story_ids: params.story_ids && params.story_ids.length > 0 ? params.story_ids : [],
  };

  return buildRequestInstance(
    (messages) => {
      const request = new messages.CreateBacklogReviewCeremonyRequest();
      request.setCreatedBy(params.created_by);
      const storyIdsList = params.story_ids && params.story_ids.length > 0 ? params.story_ids : [];
      request.setStoryIdsList(storyIdsList);
      return request;
    },
    payload
  );
}

export interface GetBacklogReviewCeremonyParams {
  ceremony_id: string;
}

export function buildGetBacklogReviewCeremonyRequest(params: GetBacklogReviewCeremonyParams): any {
  const payload = { ceremony_id: params.ceremony_id };

  return buildRequestInstance(
    (messages) => {
      const request = new messages.GetBacklogReviewCeremonyRequest();
      request.setCeremonyId(params.ceremony_id);
      return request;
    },
    payload
  );
}

export interface ListBacklogReviewCeremoniesParams {
  limit: number;
  offset: number;
  status_filter?: string;
  created_by?: string;
}

export function buildListBacklogReviewCeremoniesRequest(params: ListBacklogReviewCeremoniesParams): any {
  const payload: Record<string, unknown> = {
    limit: params.limit,
    offset: params.offset,
  };

  if (params.status_filter) {
    payload.status_filter = params.status_filter;
  }

  if (params.created_by) {
    payload.created_by = params.created_by;
  }

  return buildRequestInstance(
    (messages) => {
      const request = new messages.ListBacklogReviewCeremoniesRequest();
      request.setLimit(params.limit);
      request.setOffset(params.offset);
      if (params.status_filter) {
        request.setStatusFilter(params.status_filter);
      }
      if (params.created_by) {
        request.setCreatedBy(params.created_by);
      }
      return request;
    },
    payload
  );
}

export interface StartBacklogReviewCeremonyParams {
  ceremony_id: string;
  started_by: string;
}

export function buildStartBacklogReviewCeremonyRequest(params: StartBacklogReviewCeremonyParams): any {
  const payload = {
    ceremony_id: params.ceremony_id,
    started_by: params.started_by,
  };

  return buildRequestInstance(
    (messages) => {
      const request = new messages.StartBacklogReviewCeremonyRequest();
      request.setCeremonyId(params.ceremony_id);
      request.setStartedBy(params.started_by);
      return request;
    },
    payload
  );
}

export interface ApproveReviewPlanParams {
  ceremony_id: string;
  story_id: string;
  approved_by: string;
  po_notes: string;
  po_concerns?: string;
  priority_adjustment?: string;
  po_priority_reason?: string;
}

export function buildApproveReviewPlanRequest(params: ApproveReviewPlanParams): any {
  const payload: Record<string, unknown> = {
    ceremony_id: params.ceremony_id,
    story_id: params.story_id,
    approved_by: params.approved_by,
    po_notes: params.po_notes,
  };

  if (params.po_concerns) {
    payload.po_concerns = params.po_concerns;
  }
  if (params.priority_adjustment) {
    payload.priority_adjustment = params.priority_adjustment;
  }
  if (params.po_priority_reason) {
    payload.po_priority_reason = params.po_priority_reason;
  }

  return buildRequestInstance(
    (messages) => {
      const request = new messages.ApproveReviewPlanRequest();
      request.setCeremonyId(params.ceremony_id);
      request.setStoryId(params.story_id);
      request.setApprovedBy(params.approved_by);
      request.setPoNotes(params.po_notes);
      if (params.po_concerns) {
        request.setPoConcerns(params.po_concerns);
      }
      if (params.priority_adjustment) {
        request.setPriorityAdjustment(params.priority_adjustment);
      }
      if (params.po_priority_reason) {
        request.setPoPriorityReason(params.po_priority_reason);
      }
      return request;
    },
    payload
  );
}

export interface RejectReviewPlanParams {
  ceremony_id: string;
  story_id: string;
  rejected_by: string;
  rejection_reason: string;
}

export function buildRejectReviewPlanRequest(params: RejectReviewPlanParams): any {
  const payload = {
    ceremony_id: params.ceremony_id,
    story_id: params.story_id,
    rejected_by: params.rejected_by,
    rejection_reason: params.rejection_reason,
  };

  return buildRequestInstance(
    (messages) => {
      const request = new messages.RejectReviewPlanRequest();
      request.setCeremonyId(params.ceremony_id);
      request.setStoryId(params.story_id);
      request.setRejectedBy(params.rejected_by);
      request.setRejectionReason(params.rejection_reason);
      return request;
    },
    payload
  );
}

export interface CompleteBacklogReviewCeremonyParams {
  ceremony_id: string;
  completed_by: string;
}

export function buildCompleteBacklogReviewCeremonyRequest(params: CompleteBacklogReviewCeremonyParams): any {
  const payload = {
    ceremony_id: params.ceremony_id,
    completed_by: params.completed_by,
  };

  return buildRequestInstance(
    (messages) => {
      const request = new messages.CompleteBacklogReviewCeremonyRequest();
      request.setCeremonyId(params.ceremony_id);
      request.setCompletedBy(params.completed_by);
      return request;
    },
    payload
  );
}

// ============================================================================
// PLANNING CEREMONY (CEREMONY ENGINE) REQUEST BUILDERS
// ============================================================================

export interface StartPlanningCeremonyParams {
  ceremony_id: string;
  definition_name: string;
  story_id: string;
  requested_by: string;
  step_ids: string[];
  correlation_id?: string;
  inputs?: Record<string, string>;
}

export function buildStartPlanningCeremonyRequest(params: StartPlanningCeremonyParams): any {
  const payload: Record<string, unknown> = {
    ceremony_id: params.ceremony_id,
    definition_name: params.definition_name,
    story_id: params.story_id,
    requested_by: params.requested_by,
    step_ids: params.step_ids,
  };

  if (params.correlation_id) {
    payload.correlation_id = params.correlation_id;
  }

  if (params.inputs && Object.keys(params.inputs).length > 0) {
    payload.inputs = params.inputs;
  }

  return buildRequestInstance(
    (messages) => {
      const request = new messages.StartPlanningCeremonyRequest();
      request.setCeremonyId(params.ceremony_id);
      request.setDefinitionName(params.definition_name);
      request.setStoryId(params.story_id);
      request.setRequestedBy(params.requested_by);
      request.setStepIdsList(params.step_ids);

      if (params.correlation_id) {
        request.setCorrelationId(params.correlation_id);
      }

      if (params.inputs && Object.keys(params.inputs).length > 0 && typeof request.getInputsMap === 'function') {
        const inputsMap = request.getInputsMap();
        if (typeof inputsMap.clear === 'function') {
          inputsMap.clear();
        }
        for (const [key, value] of Object.entries(params.inputs)) {
          inputsMap.set(key, value);
        }
      }

      return request;
    },
    payload
  );
}
