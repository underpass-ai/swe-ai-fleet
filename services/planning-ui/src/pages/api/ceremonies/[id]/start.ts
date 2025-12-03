import type { APIRoute } from 'astro';
import { createGrpcClient } from '../../../../lib/grpc-client';

export const POST: APIRoute = async ({ params, request }) => {
  const { id } = params;

  if (!id) {
    return new Response(
      JSON.stringify({ success: false, message: 'Ceremony ID required' }),
      { status: 400, headers: { 'Content-Type': 'application/json' } }
    );
  }

  try {
    const body = await request.json();
    const { started_by } = body;

    if (!started_by) {
      return new Response(
        JSON.stringify({ success: false, message: 'started_by is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const client = await createGrpcClient();

    // TODO: Call StartBacklogReviewCeremony when implemented
    // const response = await client.StartBacklogReviewCeremony({
    //   ceremony_id: id,
    //   started_by,
    // });

    return new Response(
      JSON.stringify({
        success: true,
        message: 'Ceremony started successfully',
        ceremony_id: id,
      }),
      {
        status: 200,
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

