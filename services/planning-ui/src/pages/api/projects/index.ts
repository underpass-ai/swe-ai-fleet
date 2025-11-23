import type { APIRoute } from 'astro';
import { getPlanningServiceConfig } from '../../../lib/config';

/**
 * GET /api/projects
 * List all projects
 */
export const GET: APIRoute = async ({ request }) => {
  try {
    const url = new URL(request.url);
    const statusFilter = url.searchParams.get('status_filter') || '';
    const limit = parseInt(url.searchParams.get('limit') || '100');
    const offset = parseInt(url.searchParams.get('offset') || '0');

    // TODO: Connect to Planning Service gRPC
    // For now, return empty array
    // Implementation should use @grpc/grpc-js to call:
    // planning.ListProjects({ status_filter, limit, offset })

    return new Response(
      JSON.stringify({
        projects: [],
        total_count: 0,
        success: true,
        message: 'Projects retrieved (not yet connected to gRPC)',
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
 * POST /api/projects
 * Create a new project
 */
export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();
    const { name, description, owner } = body;

    if (!name || !owner) {
      return new Response(
        JSON.stringify({
          success: false,
          message: 'name and owner are required',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // TODO: Connect to Planning Service gRPC
    // Implementation should use @grpc/grpc-js to call:
    // planning.CreateProject({ name, description, owner })

    return new Response(
      JSON.stringify({
        project: {
          project_id: `project-${Date.now()}`,
          name,
          description: description || '',
          status: 'active',
          owner,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        success: true,
        message: 'Project created (not yet connected to gRPC)',
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

