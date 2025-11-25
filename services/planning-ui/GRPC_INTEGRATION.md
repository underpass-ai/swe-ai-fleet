# gRPC Integration Guide

## Overview

The Planning UI uses Astro API routes to proxy requests to the Planning Service gRPC API. Currently, the API routes are structured but not yet connected to the gRPC service.

## Current Status

✅ **Completed:**
- API routes structure (`src/pages/api/`)
- Pages and components for all CRUD operations
- Type definitions matching protobuf schemas

⚠️ **Pending:**
- gRPC client implementation in API routes
- Protobuf compilation for Node.js
- Error handling and retry logic

## Implementation Steps

### 1. Install gRPC Dependencies

```bash
npm install @grpc/grpc-js @grpc/proto-loader
```

### 2. Compile Protobuf for Node.js

The Planning Service protobuf files are in `specs/fleet/planning/v2/planning.proto`.

You need to:
1. Copy the `.proto` file to the planning-ui project
2. Compile it using `protoc` or `@grpc/proto-loader`
3. Generate TypeScript types (optional, using `ts-proto`)

### 3. Create gRPC Client Utility

Create `src/lib/grpc-client.ts`:

```typescript
import * as grpc from '@grpc/grpc-js';
import * as protoLoader from '@grpc/proto-loader';
import { getPlanningServiceConfig } from './config';

const PROTO_PATH = '../../specs/fleet/planning/v2/planning.proto';

export async function getPlanningClient() {
  const config = getPlanningServiceConfig();
  const packageDefinition = await protoLoader.load(PROTO_PATH, {
    keepCase: true,
    longs: String,
    enums: String,
    defaults: true,
    oneofs: true,
  });

  const planningProto = grpc.loadPackageDefinition(packageDefinition) as any;
  const client = new planningProto.fleet.planning.v2.PlanningService(
    `${config.grpcUrl}:${config.grpcPort}`,
    grpc.credentials.createInsecure()
  );

  return client;
}
```

### 4. Update API Routes

Example for `src/pages/api/projects/index.ts`:

```typescript
import { getPlanningClient } from '../../../lib/grpc-client';

export const GET: APIRoute = async ({ request }) => {
  try {
    const client = await getPlanningClient();
    const url = new URL(request.url);
    const statusFilter = url.searchParams.get('status_filter') || '';
    const limit = parseInt(url.searchParams.get('limit') || '100');
    const offset = parseInt(url.searchParams.get('offset') || '0');

    return new Promise((resolve, reject) => {
      client.ListProjects(
        { status_filter: statusFilter, limit, offset },
        (error: any, response: any) => {
          if (error) {
            reject(error);
          } else {
            resolve(
              new Response(JSON.stringify(response), {
                status: 200,
                headers: { 'Content-Type': 'application/json' },
              })
            );
          }
        }
      );
    });
  } catch (error) {
    // Error handling
  }
};
```

## Alternative: REST API Gateway

Instead of implementing gRPC clients in Node.js, you could create a small Python service that:
1. Exposes REST endpoints
2. Calls the Planning Service gRPC internally
3. Returns JSON responses

This would be simpler but adds another microservice to maintain.

## Environment Variables

The Planning Service URL is configured via:
- `PUBLIC_PLANNING_SERVICE_URL` (default: `http://planning.swe-ai-fleet.svc.cluster.local:50054`)
- `PUBLIC_PLANNING_SERVICE_PORT` (default: `50054`)

Note: For gRPC, you'll need the actual gRPC endpoint, not HTTP.

## Testing

Once integrated, test the API routes:

```bash
# List projects
curl http://localhost:4321/api/projects

# Create project
curl -X POST http://localhost:4321/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Project", "owner": "test-user"}'
```

## References

- [gRPC Node.js Documentation](https://grpc.io/docs/languages/node/)
- [@grpc/grpc-js](https://www.npmjs.com/package/@grpc/grpc-js)
- [Planning Service Protobuf](../specs/fleet/planning/v2/planning.proto)


