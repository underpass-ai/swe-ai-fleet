import type { APIRoute } from 'astro';
import { getPlanningClient, promisifyGrpcCall, grpcErrorToHttpStatus, isServiceError } from '../../../lib/grpc-client';
import { buildCreateStoryRequest, buildListStoriesRequest } from '../../../lib/grpc-request-builders';

/**
 * GET /api/stories
 * List stories with optional filtering
 */
export const GET: APIRoute = async ({ request }) => {
  try {
    const url = new URL(request.url);
    const stateFilter = url.searchParams.get('state') || '';
    const epicId = url.searchParams.get('epic_id') || '';
    const limit = parseInt(url.searchParams.get('limit') || '100');
    const offset = parseInt(url.searchParams.get('offset') || '0');

    const client = await getPlanningClient();

    const requestPayload = buildListStoriesRequest({
      limit,
      offset,
      state_filter: stateFilter || undefined,
      epic_id: epicId || undefined,
    });

    const response = await promisifyGrpcCall(
      (req, callback) => client.listStories(req, callback),
      requestPayload
    );

    return new Response(
      JSON.stringify({
        stories: response.stories || [],
        total_count: response.total_count || 0,
        success: response.success !== false,
        message: response.message || 'Stories retrieved successfully',
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  } catch (error) {
    if (isServiceError(error)) {
      const httpStatus = grpcErrorToHttpStatus(error);
      // gRPC error details are in error.details (set via context.set_details())
      // fallback to error.message if details is not available
      const errorMessage = (error as any).details || error.message || 'gRPC error';
      return new Response(
        JSON.stringify({
          success: false,
          message: errorMessage,
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
 * POST /api/stories
 * Create a new story
 */
export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();
    const { epic_id, title, brief, created_by } = body;

    if (!epic_id || !title) {
      return new Response(
        JSON.stringify({
          success: false,
          message: 'epic_id and title are required',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Validate brief: must be non-empty (backend will also validate)
    if (!brief || !brief.trim()) {
      return new Response(
        JSON.stringify({
          success: false,
          message: 'brief is required and cannot be empty',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    const client = await getPlanningClient();

    const requestPayload = buildCreateStoryRequest({
      epic_id,
      title,
      brief: brief.trim(),
      created_by: created_by || 'ui-user',
    });

    const response = await promisifyGrpcCall(
      (req, callback) => client.createStory(req, callback),
      requestPayload
    );

    if (!response.success || !response.story) {
      return new Response(
        JSON.stringify({
          success: false,
          message: response.message || 'Failed to create story',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    return new Response(
      JSON.stringify({
        story: response.story,
        success: true,
        message: response.message || 'Story created successfully',
      }),
      {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  } catch (error) {
    if (isServiceError(error)) {
      const httpStatus = grpcErrorToHttpStatus(error);
      // gRPC error details are in error.details (set via context.set_details())
      // fallback to error.message if details is not available
      const errorMessage = (error as any).details || error.message || 'gRPC error';
      return new Response(
        JSON.stringify({
          success: false,
          message: errorMessage,
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
