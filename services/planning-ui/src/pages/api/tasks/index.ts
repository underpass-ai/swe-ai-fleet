import type { APIRoute } from 'astro';
import { getPlanningClient, promisifyGrpcCall, grpcErrorToHttpStatus, isServiceError } from '../../../lib/grpc-client';
import { buildListTasksRequest } from '../../../lib/grpc-request-builders';

/**
 * GET /api/tasks
 * List tasks with optional filtering
 */
export const GET: APIRoute = async ({ request }) => {
  try {
    const url = new URL(request.url);
    const storyId = url.searchParams.get('story_id') || '';
    const statusFilter = url.searchParams.get('status_filter') || '';
    const planId = url.searchParams.get('plan_id') || '';
    const limit = parseInt(url.searchParams.get('limit') || '100');
    const offset = parseInt(url.searchParams.get('offset') || '0');

    const client = await getPlanningClient();

    const requestPayload = buildListTasksRequest({
      limit,
      offset,
      story_id: storyId || undefined,
      status_filter: statusFilter || undefined,
    });

    const response = await promisifyGrpcCall(
      (req, callback) => client.listTasks(req, callback),
      requestPayload
    );

    // Filter by plan_id in frontend if provided (since protobuf doesn't support it)
    let tasks = response.tasks || [];
    if (planId) {
      tasks = tasks.filter((task: any) => task.plan_id === planId);
    }

    return new Response(
      JSON.stringify({
        tasks,
        total_count: tasks.length,
        success: response.success !== false,
        message: response.message || 'Tasks retrieved successfully',
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


