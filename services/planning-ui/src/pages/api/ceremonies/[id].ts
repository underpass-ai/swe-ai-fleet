import type { APIRoute } from 'astro';
import { getPlanningClient, promisifyGrpcCall, grpcErrorToHttpStatus, isServiceError } from '../../../lib/grpc-client';
import { buildGetBacklogReviewCeremonyRequest } from '../../../lib/grpc-request-builders';

export const GET: APIRoute = async ({ params }) => {
  const { id } = params;

  if (!id) {
    return new Response(
      JSON.stringify({ success: false, message: 'Ceremony ID required' }),
      { status: 400, headers: { 'Content-Type': 'application/json' } }
    );
  }

  try {
    const client = await getPlanningClient();

    const requestPayload = buildGetBacklogReviewCeremonyRequest({
      ceremony_id: id,
    });

    const response = await promisifyGrpcCall(
      (req, callback) => client.getBacklogReviewCeremony(req, callback),
      requestPayload
    );

    if (!response.success || !response.ceremony) {
      return new Response(
        JSON.stringify({
          success: false,
          message: response.message || 'Ceremony not found',
        }),
        {
          status: 404,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    return new Response(
      JSON.stringify({
        ceremony: response.ceremony,
        success: true,
        message: response.message || 'Ceremony retrieved successfully',
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

