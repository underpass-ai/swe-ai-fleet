# gRPC Integration Guide

## Overview

The Planning UI uses Astro API routes to proxy requests to the Planning Service gRPC API. The integration is **complete** and all routes are connected to the gRPC service.

## Current Status

✅ **Completed:**
- API routes structure (`src/pages/api/`)
- Pages and components for all CRUD operations
- Type definitions matching protobuf schemas
- gRPC client implementation (`src/lib/grpc-client.ts`)
- Protobuf loading via `@grpc/proto-loader` at runtime
- Error handling and HTTP status code mapping
- All API routes integrated with gRPC (projects, epics, stories, tasks)

## Implementation Details

## Architecture

The gRPC integration uses:
1. **Runtime protobuf loading**: `@grpc/proto-loader` loads the `.proto` file at runtime (no compilation step)
2. **Singleton client pattern**: Client instance is cached and reused
3. **Error mapping**: gRPC status codes are mapped to HTTP status codes
4. **Promisified calls**: Helper function wraps callback-based gRPC calls in promises

### Key Components

1. **gRPC Client** (`src/lib/grpc-client.ts`):
   - Singleton pattern for client reuse
   - Runtime protobuf loading via `@grpc/proto-loader`
   - Automatic path resolution (development, production, container)
   - Error mapping from gRPC status codes to HTTP status codes
   - Promisified wrapper for callback-based gRPC calls

2. **Configuration** (`src/lib/config.ts`):
   - Reads environment variables for Planning Service connection
   - Extracts hostname (removes HTTP protocol if present)
   - Default values for development

3. **API Routes** (`src/pages/api/`):
   - All routes use `getPlanningClient()` and `promisifyGrpcCall()`
   - Consistent error handling across all endpoints
   - Proper HTTP status code mapping

### Protobuf Loading

The protobuf file is:
- Copied to container at build time via Dockerfile
- Loaded at runtime (no compilation step)
- Located via multiple fallback paths for different environments

## Environment Variables

The Planning Service connection is configured via:
- `PUBLIC_PLANNING_SERVICE_URL`: Hostname only (no protocol prefix)
  - Default: `planning.swe-ai-fleet.svc.cluster.local`
  - **Important**: Do not include `http://` or `https://` prefix
- `PUBLIC_PLANNING_SERVICE_PORT`: gRPC port
  - Default: `50054`

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


