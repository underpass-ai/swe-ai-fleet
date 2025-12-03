import type { APIRoute } from 'astro';
import { createGrpcClient } from '../../../lib/grpc-client';

export const GET: APIRoute = async ({ params }) => {
  const { id } = params;

  if (!id) {
    return new Response(
      JSON.stringify({ success: false, message: 'Ceremony ID required' }),
      { status: 400, headers: { 'Content-Type': 'application/json' } }
    );
  }

  try {
    const client = await createGrpcClient();

    // TODO: Call GetBacklogReviewCeremony when implemented
    // For now, return mock data
    const ceremony = {
      ceremony_id: id,
      story_ids: ['ST-123', 'ST-124', 'ST-125'],
      status: 'DRAFT',
      review_results: [],
      created_by: 'john.doe@example.com',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    return new Response(
      JSON.stringify({ ceremony, success: true }),
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

