# Core Orchestrator

Reusable domain and use-case layer for multi-agent deliberation and orchestration.

## Scope

`core/orchestrator` contains:

- Domain model for agents, tasks, constraints, and check/scoring results
- Deliberation and orchestration use cases:
  - `peer_deliberation_usecase`
  - `orchestrate_usecase`
  - `dispatch_usecase`
  - `deliberate_async_usecase`
- Configuration module:
  - `system_config`
  - `role_config`
  - `vllm_config`
  - `agent_configuration`
- DTOs used by service adapters

## Runtime Role

This module is the logic engine used by `services/orchestrator`.
The service layer adds transport (gRPC), messaging (NATS), and adapter wiring.

## Tests

```bash
make test-module MODULE=core/orchestrator
```
