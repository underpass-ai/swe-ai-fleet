import type { APIRoute } from 'astro';
import { getPlanningClient, promisifyGrpcCall, grpcErrorToHttpStatus, isServiceError } from '../../../lib/grpc-client';

/**
 * GET /api/tasks
 * List tasks with optional filtering
 */
export const GET: APIRoute = async ({ request }) => {
  try {
    const url = new URL(request.url);
    const storyId = url.searchParams.get('story_id') || '';
    const statusFilter = url.searchParams.get('status_filter') || '';
    const limit = parseInt(url.searchParams.get('limit') || '100');
    const offset = parseInt(url.searchParams.get('offset') || '0');

    const client = await getPlanningClient();

    const requestPayload: any = {
      limit,
      offset,
    };

    if (storyId) {
      requestPayload.story_id = storyId;
    }

    if (statusFilter) {
      requestPayload.status_filter = statusFilter;
    }

    const response = await promisifyGrpcCall(
      (req, callback) => client.ListTasks(req, callback),
      requestPayload
    );

    return new Response(
      JSON.stringify({
        tasks: response.tasks || [],
        total_count: response.total_count || 0,
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


