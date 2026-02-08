# Core Context

Domain and application logic for context rehydration, graph projections, and role-based visibility.

## Scope

`core/context` provides:

- Rich domain model for Project, Epic, Story, Task, Decision, milestones, and graph relations
- Application services:
  - `SessionRehydrationService`
  - `RBACContextService`
- Use cases for:
  - planning event synchronization (`synchronize_*_from_planning`)
  - story phase transitions and plan approvals
  - context update/rehydration response publishing
  - graph relationship queries
- Ports for config, graph query/command, messaging, planning reads, and authorization
- Adapters for Neo4j, Redis/Valkey reads, and environment config loading

## Integration

Primary consumer:

- `services/context`

Secondary usage:

- Reporting adapters that reuse context-side Neo4j query primitives

## Configuration Notes

`core/context/adapters/env_config_adapter.py` enforces:

- `NEO4J_PASSWORD` is required
- `ENABLE_NATS` defaults to `true`

## Tests

```bash
make test-module MODULE=core/context
```
