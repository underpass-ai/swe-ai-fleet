import type { APIRoute } from 'astro';
import { getPlanningClient, promisifyGrpcCall, grpcErrorToHttpStatus, isServiceError } from '../../../lib/grpc-client';
import { buildListBacklogReviewCeremoniesRequest, buildCreateBacklogReviewCeremonyRequest } from '../../../lib/grpc-request-builders';

export const GET: APIRoute = async ({ url }) => {
  try {
    const urlObj = new URL(url);
    const statusFilter = urlObj.searchParams.get('status') || '';
    const limit = parseInt(urlObj.searchParams.get('limit') || '100');
    const offset = parseInt(urlObj.searchParams.get('offset') || '0');

    const client = await getPlanningClient();

    const requestPayload = buildListBacklogReviewCeremoniesRequest({
      limit,
      offset,
      status_filter: statusFilter || undefined,
    });

    const response = await promisifyGrpcCall(
      (req, callback) => client.listBacklogReviewCeremonies(req, callback),
      requestPayload
    );

    return new Response(
      JSON.stringify({
        ceremonies: response.ceremonies || [],
        total_count: response.total_count || 0,
        success: response.success !== false,
        message: response.message || 'Ceremonies retrieved successfully',
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

export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();
    const { created_by, story_ids } = body;

    if (!created_by) {
      return new Response(
        JSON.stringify({
          success: false,
          message: 'created_by is required',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    const client = await getPlanningClient();

    const requestPayload = buildCreateBacklogReviewCeremonyRequest({
      created_by,
      story_ids: Array.isArray(story_ids) ? story_ids : undefined,
    });

    const response = await promisifyGrpcCall(
      (req, callback) => client.createBacklogReviewCeremony(req, callback),
      requestPayload
    );

    if (!response.success || !response.ceremony) {
      return new Response(
        JSON.stringify({
          success: false,
          message: response.message || 'Failed to create ceremony',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    return new Response(
      JSON.stringify({
        ceremony_id: response.ceremony.ceremony_id,
        ceremony: response.ceremony,
        success: true,
        message: response.message || 'Ceremony created successfully',
      }),
      {
        status: 201,
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

