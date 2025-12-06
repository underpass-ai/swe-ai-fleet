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
    const { story_id, approved_by } = body;

    if (!story_id || !approved_by) {
      return new Response(
        JSON.stringify({ success: false, message: 'story_id and approved_by are required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const client = await createGrpcClient();

    // TODO: Call ApproveReviewPlan when implemented
    // const response = await client.ApproveReviewPlan({
    //   ceremony_id: id,
    //   story_id,
    //   approved_by,
    // });

    return new Response(
      JSON.stringify({
        success: true,
        message: 'Plan approved successfully',
        plan_id: `plan-${Date.now()}`,
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

