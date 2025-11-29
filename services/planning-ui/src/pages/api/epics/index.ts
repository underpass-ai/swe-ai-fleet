import type { APIRoute } from 'astro';
import { getPlanningClient, promisifyGrpcCall, grpcErrorToHttpStatus, isServiceError } from '../../../lib/grpc-client';
import { buildCreateEpicRequest, buildListEpicsRequest } from '../../../lib/grpc-request-builders';

/**
 * GET /api/epics
 * List epics with optional filtering
 */
export const GET: APIRoute = async ({ request }) => {
  try {
    const url = new URL(request.url);
    const projectId = url.searchParams.get('project_id') || '';
    const statusFilter = url.searchParams.get('status_filter') || '';
    const limit = parseInt(url.searchParams.get('limit') || '100');
    const offset = parseInt(url.searchParams.get('offset') || '0');

    const client = await getPlanningClient();

    const requestPayload = buildListEpicsRequest({
      limit,
      offset,
      project_id: projectId || undefined,
      status_filter: statusFilter || undefined,
    });

    const response = await promisifyGrpcCall(
      (req, callback) => client.listEpics(req, callback),
      requestPayload
    );

    return new Response(
      JSON.stringify({
        epics: response.epics || [],
        total_count: response.total_count || 0,
        success: response.success !== false,
        message: response.message || 'Epics retrieved successfully',
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

/**
 * POST /api/epics
 * Create a new epic
 */
export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();
    const { project_id, title, description } = body;

    if (!project_id || !title) {
      return new Response(
        JSON.stringify({
          success: false,
          message: 'project_id and title are required',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    const client = await getPlanningClient();

    const requestPayload = buildCreateEpicRequest({
      project_id,
      title,
      description: description || '',
    });

    const response = await promisifyGrpcCall(
      (req, callback) => client.createEpic(req, callback),
      requestPayload
    );

    if (!response.success || !response.epic) {
      return new Response(
        JSON.stringify({
          success: false,
          message: response.message || 'Failed to create epic',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    return new Response(
      JSON.stringify({
        epic: response.epic,
        success: true,
        message: response.message || 'Epic created successfully',
      }),
      {
        status: 201,
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


