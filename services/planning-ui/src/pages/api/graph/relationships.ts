import type { APIRoute } from 'astro';
import { getContextClient, promisifyGrpcCall, grpcErrorToHttpStatus, isServiceError } from '../../../lib/context-grpc-client';

/**
 * GET /api/graph/relationships
 * Get Neo4j graph relationships for a node and its neighbors
 * 
 * Query params:
 * - node_id: Node identifier (e.g., story_id, epic_id, task_id, project_id)
 * - node_type: Node type (Project, Epic, Story, Task)
 * - depth: Traversal depth (default: 2, max: 3)
 */
export const GET: APIRoute = async ({ request }) => {
  try {
    const url = new URL(request.url);
    const nodeId = url.searchParams.get('node_id');
    const nodeType = url.searchParams.get('node_type') || 'Story';
    const depth = Math.min(Math.max(parseInt(url.searchParams.get('depth') || '2'), 1), 3);

    if (!nodeId) {
      return new Response(
        JSON.stringify({
          success: false,
          message: 'node_id is required',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    const client = getContextClient();

    // Build request payload
    const requestPayload = {
      node_id: nodeId,
      node_type: nodeType,
      depth: depth,
    };

    // Call Context Service GetGraphRelationships
    const response = await promisifyGrpcCall(
      (req, callback) => client.getGraphRelationships(req, callback),
      requestPayload
    );

    if (!response.success) {
      return new Response(
        JSON.stringify({
          success: false,
          message: response.message || 'Failed to get graph relationships',
        }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Convert protobuf response to JSON
    const result = {
      success: true,
      node: {
        id: response.node?.id || nodeId,
        type: response.node?.type || nodeType,
        labels: response.node?.labels || [],
        properties: response.node?.properties || {},
        title: response.node?.title || nodeId,
      },
      neighbors: (response.neighbors || []).map((n: any) => ({
        id: n.id,
        type: n.type,
        labels: n.labels || [],
        properties: n.properties || {},
        title: n.title || n.id,
      })),
      relationships: (response.relationships || []).map((r: any) => ({
        from_node_id: r.from_node_id,
        to_node_id: r.to_node_id,
        type: r.type,
        properties: r.properties || {},
      })),
      message: response.message || 'Graph relationships retrieved successfully',
    };

    return new Response(
      JSON.stringify(result),
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

