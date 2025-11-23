import type { APIRoute } from 'astro';

/**
 * GET /api/epics
 * List epics with optional filtering
 */
export const GET: APIRoute = async ({ request }) => {
  try {
    const url = new URL(request.url);
    const projectId = url.searchParams.get('project_id') || '';
    const statusFilter = url.searchParams.get('status_filter') || '';
    const limit = parseInt(url.searchParams.get('limit') || '100');
    const offset = parseInt(url.searchParams.get('offset') || '0');

    // TODO: Connect to Planning Service gRPC
    // Implementation should use @grpc/grpc-js to call:
    // planning.ListEpics({ project_id: projectId, status_filter: statusFilter, limit, offset })

    return new Response(
      JSON.stringify({
        epics: [],
        total_count: 0,
        success: true,
        message: 'Epics retrieved (not yet connected to gRPC)',
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

/**
 * POST /api/epics
 * Create a new epic
 */
export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();
    const { project_id, title, description } = body;

    if (!project_id || !title) {
      return new Response(
        JSON.stringify({
          success: false,
          message: 'project_id and title are required',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // TODO: Connect to Planning Service gRPC
    // Implementation should use @grpc/grpc-js to call:
    // planning.CreateEpic({ project_id, title, description })

    return new Response(
      JSON.stringify({
        epic: {
          epic_id: `epic-${Date.now()}`,
          project_id,
          title,
          description: description || '',
          status: 'active',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        success: true,
        message: 'Epic created (not yet connected to gRPC)',
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

