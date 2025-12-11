import type { APIRoute } from 'astro';
import { getPlanningClient, promisifyGrpcCall, grpcErrorToHttpStatus, isServiceError } from '../../../../lib/grpc-client';
import { buildCompleteBacklogReviewCeremonyRequest } from '../../../../lib/grpc-request-builders';

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
    const { completed_by } = body;

    if (!completed_by) {
      return new Response(
        JSON.stringify({ success: false, message: 'completed_by is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const client = await getPlanningClient();

    const requestPayload = buildCompleteBacklogReviewCeremonyRequest({
      ceremony_id: id,
      completed_by,
    });

    const response = await promisifyGrpcCall(
      (req, callback) => client.completeBacklogReviewCeremony(req, callback),
      requestPayload
    );

    if (!response.success) {
      return new Response(
        JSON.stringify({
          success: false,
          message: response.message || 'Failed to complete ceremony',
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
        success: true,
        message: response.message || 'Ceremony completed successfully',
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

