import type { APIRoute } from 'astro';
import { getPlanningClient, promisifyGrpcCall, grpcErrorToHttpStatus, isServiceError } from '../../../lib/grpc-client';
import { buildCreateProjectRequest, buildListProjectsRequest } from '../../../lib/grpc-request-builders';

/**
 * GET /api/projects
 * List all projects
 */
export const GET: APIRoute = async ({ request }) => {
  try {
    const url = new URL(request.url);
    const statusFilter = url.searchParams.get('status_filter') || '';
    const limit = parseInt(url.searchParams.get('limit') || '100');
    const offset = parseInt(url.searchParams.get('offset') || '0');

    const client = await getPlanningClient();

    const requestPayload = buildListProjectsRequest({
      limit,
      offset,
      status_filter: statusFilter || undefined,
    });

    const response = await promisifyGrpcCall(
      (req, callback) => client.listProjects(req, callback),
      requestPayload
    );

    return new Response(
      JSON.stringify({
        projects: response.projects || [],
        total_count: response.total_count || 0,
        success: response.success !== false,
        message: response.message || 'Projects retrieved successfully',
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
 * POST /api/projects
 * Create a new project
 */
export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();
    const { name, description, owner } = body;

    if (!name || !owner) {
      return new Response(
        JSON.stringify({
          success: false,
          message: 'name and owner are required',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    const client = await getPlanningClient();

    const requestPayload = buildCreateProjectRequest({
      name,
      description: description || '',
      owner,
    });

    const response = await promisifyGrpcCall(
      (req, callback) => client.createProject(req, callback),
      requestPayload
    );

    if (!response.success || !response.project) {
      return new Response(
        JSON.stringify({
          success: false,
          message: response.message || 'Failed to create project',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    return new Response(
      JSON.stringify({
        project: response.project,
        success: true,
        message: response.message || 'Project created successfully',
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


