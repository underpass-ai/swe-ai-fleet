import type { APIRoute } from 'astro';
import {
  getPlanningClient,
  promisifyGrpcCall,
  grpcErrorToHttpStatus,
  isServiceError,
} from '../../../../lib/grpc-client';
import { buildListPlanningCeremoniesRequest } from '../../../../lib/grpc-request-builders';

function parsePagination(value: string | null, fallback: number): number {
  const parsed = Number.parseInt(value || '', 10);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function splitInstanceId(instanceId: string): { ceremony_id: string; story_id: string } {
  const parts = String(instanceId || '').split(':');
  if (parts.length >= 2) {
    const storyId = parts[parts.length - 1];
    const ceremonyId = parts.slice(0, -1).join(':');
    return { ceremony_id: ceremonyId, story_id: storyId };
  }
  return { ceremony_id: instanceId, story_id: '' };
}

function normalizeCeremony(raw: any): Record<string, unknown> {
  const instance_id = String(raw?.instance_id || '');
  const fallbackIds = splitInstanceId(instance_id);
  return {
    instance_id,
    ceremony_id: String(raw?.ceremony_id || fallbackIds.ceremony_id),
    story_id: String(raw?.story_id || fallbackIds.story_id),
    definition_name: String(raw?.definition_name || ''),
    current_state: String(raw?.current_state || ''),
    status: String(raw?.status || raw?.current_state || ''),
    correlation_id: String(raw?.correlation_id || ''),
    step_status: raw?.step_status || {},
    step_outputs: raw?.step_outputs || {},
    created_at: String(raw?.created_at || ''),
    updated_at: String(raw?.updated_at || ''),
  };
}

export const GET: APIRoute = async ({ url }) => {
  try {
    const stateFilter = url.searchParams.get('status') || url.searchParams.get('state') || '';
    const definitionFilter =
      url.searchParams.get('definition_filter') ||
      url.searchParams.get('definition_name') ||
      '';
    const storyId = url.searchParams.get('story_id') || '';
    const limit = Math.max(parsePagination(url.searchParams.get('limit'), 100), 1);
    const offset = Math.max(parsePagination(url.searchParams.get('offset'), 0), 0);

    const client = await getPlanningClient();
    const requestPayload = buildListPlanningCeremoniesRequest({
      limit,
      offset,
      state_filter: stateFilter || undefined,
      definition_filter: definitionFilter || undefined,
      story_id: storyId || undefined,
    });

    const response = await promisifyGrpcCall(
      (req, callback) => client.listPlanningCeremonies(req, callback),
      requestPayload
    );

    const ceremonies = Array.isArray(response.ceremonies)
      ? response.ceremonies.map(normalizeCeremony)
      : [];

    return new Response(
      JSON.stringify({
        ceremonies,
        total_count: response.total_count || 0,
        success: response.success !== false,
        message: response.message || 'Planning ceremonies retrieved successfully',
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  } catch (error) {
    if (isServiceError(error)) {
      const httpStatus = grpcErrorToHttpStatus(error);
      return new Response(
        JSON.stringify({
          success: false,
          message: error.message || 'gRPC error',
          code: error.code,
        }),
        {
          status: httpStatus,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    return new Response(
      JSON.stringify({
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error',
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
};
