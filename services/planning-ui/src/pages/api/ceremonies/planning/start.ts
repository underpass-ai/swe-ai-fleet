import type { APIRoute } from 'astro';
import {
  getPlanningClient,
  promisifyGrpcCall,
  grpcErrorToHttpStatus,
  isServiceError,
} from '../../../../lib/grpc-client';
import { buildStartPlanningCeremonyRequest } from '../../../../lib/grpc-request-builders';

function normalizeString(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

function normalizeStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => (typeof item === 'string' ? item.trim() : ''))
    .filter((item) => item.length > 0);
}

function normalizeInputs(value: unknown): Record<string, string> | null {
  if (value === undefined || value === null) {
    return {};
  }

  if (typeof value !== 'object' || Array.isArray(value)) {
    return null;
  }

  const result: Record<string, string> = {};
  for (const [key, raw] of Object.entries(value as Record<string, unknown>)) {
    if (!key) {
      continue;
    }
    result[key] = typeof raw === 'string' ? raw : JSON.stringify(raw);
  }
  return result;
}

function buildCeremonyId(providedId: string, definitionName: string): string {
  if (providedId) {
    return providedId;
  }

  const safeDefinition = definitionName
    .toLowerCase()
    .replace(/[^a-z0-9_-]/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');

  const suffix = Date.now().toString(36);
  return `planning-${safeDefinition || 'ceremony'}-${suffix}`;
}

export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();

    const definition_name = normalizeString(body?.definition_name);
    const story_id = normalizeString(body?.story_id);
    const requested_by = normalizeString(body?.requested_by);
    const ceremony_id = buildCeremonyId(
      normalizeString(body?.ceremony_id),
      definition_name
    );
    const correlation_id = normalizeString(body?.correlation_id) || undefined;
    const step_ids = normalizeStringArray(body?.step_ids);
    const inputs = normalizeInputs(body?.inputs);

    if (!definition_name) {
      return new Response(
        JSON.stringify({ success: false, message: 'definition_name is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    if (!story_id) {
      return new Response(
        JSON.stringify({ success: false, message: 'story_id is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    if (!requested_by) {
      return new Response(
        JSON.stringify({ success: false, message: 'requested_by is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    if (step_ids.length === 0) {
      return new Response(
        JSON.stringify({
          success: false,
          message: 'step_ids is required and cannot be empty',
        }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    if (inputs === null) {
      return new Response(
        JSON.stringify({
          success: false,
          message: 'inputs must be a JSON object (key/value)',
        }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const client = await getPlanningClient();

    const requestPayload = buildStartPlanningCeremonyRequest({
      ceremony_id,
      definition_name,
      story_id,
      requested_by,
      step_ids,
      correlation_id,
      inputs,
    });

    const response = await promisifyGrpcCall(
      (req, callback) => client.startPlanningCeremony(req, callback),
      requestPayload
    );

    const started = Boolean(response.instance_id);
    const statusCode = started ? 202 : 400;

    return new Response(
      JSON.stringify({
        success: started,
        ceremony_id,
        instance_id: response.instance_id || '',
        status: response.status || (started ? 'accepted' : ''),
        message: response.message || (started ? 'Planning ceremony started' : 'Planning ceremony could not be started'),
        correlation_id: correlation_id || null,
      }),
      {
        status: statusCode,
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
