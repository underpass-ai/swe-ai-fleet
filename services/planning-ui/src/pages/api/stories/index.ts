import type { APIRoute } from 'astro';

/**
 * GET /api/stories
 * List stories with optional filtering
 */
export const GET: APIRoute = async ({ request }) => {
  try {
    const url = new URL(request.url);
    const stateFilter = url.searchParams.get('state') || '';
    const limit = parseInt(url.searchParams.get('limit') || '100');
    const offset = parseInt(url.searchParams.get('offset') || '0');

    // TODO: Connect to Planning Service gRPC
    // Implementation should use @grpc/grpc-js to call:
    // planning.ListStories({ state_filter: stateFilter, limit, offset })

    return new Response(
      JSON.stringify({
        stories: [],
        total_count: 0,
        success: true,
        message: 'Stories retrieved (not yet connected to gRPC)',
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
 * POST /api/stories
 * Create a new story
 */
export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();
    const { epic_id, title, brief, created_by } = body;

    if (!epic_id || !title) {
      return new Response(
        JSON.stringify({
          success: false,
          message: 'epic_id and title are required',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // TODO: Connect to Planning Service gRPC
    // Implementation should use @grpc/grpc-js to call:
    // planning.CreateStory({ epic_id, title, brief, created_by })

    return new Response(
      JSON.stringify({
        story: {
          story_id: `story-${Date.now()}`,
          epic_id,
          title,
          brief: brief || '',
          state: 'BACKLOG',
          dor_score: 0,
          created_by: created_by || 'ui-user',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        success: true,
        message: 'Story created (not yet connected to gRPC)',
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


