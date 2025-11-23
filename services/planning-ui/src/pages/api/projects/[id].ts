import type { APIRoute } from 'astro';

/**
 * GET /api/projects/[id]
 * Get a single project by ID
 */
export const GET: APIRoute = async ({ params }) => {
  try {
    const { id } = params;

    if (!id) {
      return new Response(
        JSON.stringify({
          success: false,
          message: 'project_id is required',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // TODO: Connect to Planning Service gRPC
    // Implementation should use @grpc/grpc-js to call:
    // planning.GetProject({ project_id: id })

    return new Response(
      JSON.stringify({
        project: null,
        success: false,
        message: 'Project not found (not yet connected to gRPC)',
      }),
      {
        status: 404,
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

