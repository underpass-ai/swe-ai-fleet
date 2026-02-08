# Core Bounded Contexts

This document reflects all first-level contexts under `core/`.

## Context Inventory

| Context | Purpose | Primary Consumers |
|---|---|---|
| `core/agents_and_tools` | Agent execution logic and tool abstractions | `core/ray_jobs`, orchestrator-side adapters |
| `core/ceremony_engine` | YAML-defined ceremony runner and step handlers | `services/planning_ceremony_processor` |
| `core/context` | Rehydration domain, graph projections, scope policy | `services/context` |
| `core/memory` | Redis stream-backed session memory primitives | Shared infrastructure utilities |
| `core/orchestrator` | Deliberation and orchestration domain/use cases | `services/orchestrator` |
| `core/ray_jobs` | Ray worker payload (execute task, publish result) | `services/ray_executor` |
| `core/reports` | Markdown report generation from planning + graph data | Reporting workflows and scripts |
| `core/shared` | Shared kernel (events, idempotency, RBAC action model) | Most services and processors |

## Cross-Cutting Contracts

Event envelope and parser:

- `core/shared/events/event_envelope.py`
- `core/shared/events/infrastructure/required_envelope_parser.py`

Idempotency primitives:

- `core/shared/idempotency/idempotency_port.py`
- `core/shared/idempotency/infrastructure/valkey_idempotency_adapter.py`

These contracts are reused by consumers across Planning, Context, Orchestrator, and processor services.

## Context-Level Documentation

Each context has a dedicated README in `core/*/README.md` with implementation-level details.
