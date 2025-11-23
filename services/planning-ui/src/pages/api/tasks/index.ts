import type { APIRoute } from 'astro';

/**
 * GET /api/tasks
 * List tasks with optional filtering
 */
export const GET: APIRoute = async ({ request }) => {
  try {
    const url = new URL(request.url);
    const storyId = url.searchParams.get('story_id') || '';
    const statusFilter = url.searchParams.get('status_filter') || '';
    const limit = parseInt(url.searchParams.get('limit') || '100');
    const offset = parseInt(url.searchParams.get('offset') || '0');

    // TODO: Connect to Planning Service gRPC
    // Implementation should use @grpc/grpc-js to call:
    // planning.ListTasks({ story_id: storyId, status_filter: statusFilter, limit, offset })

    return new Response(
      JSON.stringify({
        tasks: [],
        total_count: 0,
        success: true,
        message: 'Tasks retrieved (not yet connected to gRPC)',
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

