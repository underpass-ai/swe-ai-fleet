import type { APIRoute } from 'astro';

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

    // TODO: Connect to Planning Service gRPC
    // Implementation should use @grpc/grpc-js to call:
    // planning.TransitionStory({ story_id: id, target_state, transitioned_by })

    return new Response(
      JSON.stringify({
        story: null,
        success: false,
        message: 'Transition not yet implemented (not connected to gRPC)',
      }),
      {
        status: 501,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  } catch (error) {
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

