import type { APIRoute } from 'astro';
import { getPlanningClient, promisifyGrpcCall, grpcErrorToHttpStatus, isServiceError } from '../../../lib/grpc-client';
import { buildGetStoryRequest } from '../../../lib/grpc-request-builders';

/**
 * GET /api/stories/[id]
 * Get a single story by ID
 */
export const GET: APIRoute = async ({ params }) => {
  try {
    const { id } = params;

    if (!id) {
      return new Response(
        JSON.stringify({
          success: false,
          message: 'story_id is required',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    const client = await getPlanningClient();

    const requestPayload = buildGetStoryRequest({
      story_id: id,
    });

    const response = await promisifyGrpcCall(
      (req, callback) => client.getStory(req, callback),
      requestPayload
    );

    // GetStory returns Story directly, not wrapped in response
    if (!response || !response.story_id) {
      return new Response(
        JSON.stringify({
          success: false,
          message: 'Story not found',
        }),
        {
          status: 404,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    return new Response(
      JSON.stringify({
        story: response,
        success: true,
        message: 'Story retrieved successfully',
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


