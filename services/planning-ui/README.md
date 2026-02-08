# Planning UI

Astro SSR web UI for Planning and ceremony flows.

## Stack

- Astro 5 + TypeScript
- Tailwind CSS 4
- Server-side gRPC clients (`@grpc/grpc-js`) for Planning and Context services

## Implemented Features

- Project, Epic, Story, and Task pages
- Backlog review ceremony pages
- Planning ceremony start flow (`/api/ceremonies/planning/start`)
- Graph relationships bridge endpoint (`/api/graph/relationships`)
- API routes under `src/pages/api/*` for CRUD and ceremony actions

## Known Gap

Task-derivation ceremony start is intentionally backend-stubbed:

- `services/planning-ui/src/pages/api/ceremonies/task-derivation/[id]/start-derivation.ts`
- Returns HTTP `501 Not Implemented`

## Configuration

Planning gRPC target:

- `PUBLIC_PLANNING_SERVICE_URL` (default: `planning.swe-ai-fleet.svc.cluster.local`)
- `PUBLIC_PLANNING_SERVICE_PORT` (default: `50054`)

Context gRPC target:

- `PUBLIC_CONTEXT_SERVICE_URL` (default: `context-service.swe-ai-fleet.svc.cluster.local`)
- `PUBLIC_CONTEXT_SERVICE_PORT` (default: `50054`)

## Scripts

From `services/planning-ui/package.json`:

- `npm run dev`
- `npm run build` (runs `generate-grpc` first)
- `npm run preview`
- `npm run test`
- `npm run test:coverage`

## Local Run

```bash
cd services/planning-ui
npm ci
npm run dev
```
