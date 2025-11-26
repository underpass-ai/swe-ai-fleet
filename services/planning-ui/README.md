# Planning UI

Astro-based frontend for the SWE AI Fleet Planning Service.

## Overview

This UI provides a web interface for managing:
- **Projects**: Root of the work hierarchy
- **Epics**: Groups of related stories
- **Stories**: User stories with FSM state management
- **Tasks**: Atomic work units derived from plans

## Architecture

- **Framework**: Astro 5.x with TypeScript
- **Styling**: Tailwind CSS 4.x
- **Build**: Server-side rendering (SSR) with Node.js adapter
- **Deployment**: Node.js container running Astro server
- **API Routes**: Server-side API endpoints that proxy to Planning Service gRPC

## Development

### Prerequisites

- Node.js 20+
- npm

### Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Environment Variables

Set these in `.env` or at build time:

```bash
# gRPC connection (hostname only, no protocol)
PUBLIC_PLANNING_SERVICE_URL=planning.swe-ai-fleet.svc.cluster.local
PUBLIC_PLANNING_SERVICE_PORT=50054
```

**Note**: The URL should contain only the hostname (no `http://` or `https://` prefix) since gRPC uses its own protocol.

## Building Docker Image

```bash
# Build image
podman build -t planning-ui:latest .

# Run container
podman run -p 8080:80 planning-ui:latest
```

## Integration with Planning Service

The Planning Service exposes a gRPC API on port 50051. Since browsers cannot directly call gRPC, you have two options:

1. **gRPC-Web Proxy**: Use Envoy or similar to proxy gRPC calls to gRPC-Web
2. **REST API Gateway**: Create a REST API that wraps the gRPC service
3. **Server-Side API Routes**: Use Astro API routes to proxy requests (recommended for this project)

### Recommended Approach: Astro API Routes

Create API routes in `src/pages/api/` that call the Planning Service gRPC API and return JSON.

Example structure:
```
src/pages/api/
  projects/
    index.ts      # GET /api/projects (list)
    [id].ts       # GET /api/projects/[id] (get one)
  stories/
    index.ts      # GET /api/stories (list)
    [id].ts       # GET /api/stories/[id] (get one)
    transition.ts # POST /api/stories/transition
```

## Project Structure

```
services/planning-ui/
├── src/
│   ├── layouts/        # Layout components
│   ├── pages/          # Astro pages (routes)
│   ├── components/     # Reusable components
│   ├── lib/            # Utilities and types
│   └── styles/         # Global styles
├── public/             # Static assets
├── astro.config.mjs    # Astro configuration
├── package.json
├── Dockerfile
└── README.md
```

## Features

- [x] Basic Astro setup with Tailwind CSS
- [x] Project management UI (list, detail, create)
- [x] Epic management UI (list, detail, create)
- [x] Story management UI with FSM state transitions (list, detail, create, transition)
- [x] Task management UI (list)
- [x] API routes structure
- [x] gRPC client integration in API routes
- [x] Planning Service gRPC integration (all CRUD operations)
- [ ] Real-time updates (via WebSocket or polling)

## Deployment

The UI is deployed as a static site served by Nginx. It connects to the Planning Service via gRPC (through API routes or a proxy).

For Kubernetes deployment, see `deploy/k8s/30-microservices/planning-ui.yaml` (to be created).
