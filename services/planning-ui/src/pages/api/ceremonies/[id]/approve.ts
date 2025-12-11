import type { APIRoute } from 'astro';
import { getPlanningClient, promisifyGrpcCall, grpcErrorToHttpStatus, isServiceError } from '../../../../lib/grpc-client';
import { buildApproveReviewPlanRequest } from '../../../../lib/grpc-request-builders';

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
    const { story_id, approved_by, po_notes, po_concerns, priority_adjustment, po_priority_reason } = body;

    if (!story_id || !approved_by || !po_notes) {
      return new Response(
        JSON.stringify({
          success: false,
          message: 'story_id, approved_by, and po_notes are required',
        }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const client = await getPlanningClient();

    const requestPayload = buildApproveReviewPlanRequest({
      ceremony_id: id,
      story_id,
      approved_by,
      po_notes,
      po_concerns,
      priority_adjustment,
      po_priority_reason,
    });

    const response = await promisifyGrpcCall(
      (req, callback) => client.approveReviewPlan(req, callback),
      requestPayload
    );

    if (!response.success) {
      return new Response(
        JSON.stringify({
          success: false,
          message: response.message || 'Failed to approve plan',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    return new Response(
      JSON.stringify({
        ceremony: response.ceremony,
        plan_id: response.plan_id,
        success: true,
        message: response.message || 'Plan approved successfully',
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

