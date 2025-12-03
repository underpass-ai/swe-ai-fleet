import type { APIRoute } from 'astro';
import { createGrpcClient } from '../../../lib/grpc-client';

export const GET: APIRoute = async ({ url }) => {
  const statusFilter = url.searchParams.get('status');

  try {
    const client = await createGrpcClient();

    // TODO: Call ListBacklogReviewCeremonies when implemented
    // For now, return mock data
    const ceremonies = [
      {
        ceremony_id: 'ceremony-demo-001',
        story_ids: ['ST-123', 'ST-124', 'ST-125'],
        status: 'DRAFT',
        review_results: [],
        created_by: 'john.doe@example.com',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }
    ];

    const filtered = statusFilter
      ? ceremonies.filter(c => c.status === statusFilter)
      : ceremonies;

    return new Response(
      JSON.stringify({
        ceremonies: filtered,
        total_count: filtered.length,
        success: true,
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

export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();
    const { created_by, story_ids } = body;

    if (!created_by || !Array.isArray(story_ids)) {
      return new Response(
        JSON.stringify({
          success: false,
          message: 'created_by and story_ids are required',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    const client = await createGrpcClient();

    // TODO: Call CreateBacklogReviewCeremony when implemented
    // For now, return mock response
    const ceremony_id = `ceremony-${Date.now()}`;

    return new Response(
      JSON.stringify({
        ceremony_id,
        success: true,
        message: 'Ceremony created successfully',
      }),
      {
        status: 201,
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

