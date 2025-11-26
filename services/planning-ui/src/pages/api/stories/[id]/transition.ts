import type { APIRoute } from 'astro';
import { getPlanningClient, promisifyGrpcCall, grpcErrorToHttpStatus, isServiceError } from '../../../../lib/grpc-client';

/**
 * POST /api/stories/[id]/transition
 * Transition a story to a new state (FSM)
 */
export const POST: APIRoute = async ({ params, request }) => {
  try {
    const { id } = params;
    const body = await request.json();
    const { target_state, transitioned_by } = body;

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

    if (!target_state) {
      return new Response(
        JSON.stringify({
          success: false,
          message: 'target_state is required',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    const client = await getPlanningClient();

    const requestPayload = {
      story_id: id,
      target_state,
      transitioned_by: transitioned_by || 'ui-user',
    };

    const response = await promisifyGrpcCall(
      (req, callback) => client.TransitionStory(req, callback),
      requestPayload
    );

    if (!response.success || !response.story) {
      return new Response(
        JSON.stringify({
          success: false,
          message: response.message || 'Failed to transition story',
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
        message: response.message || 'Story transitioned successfully',
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


