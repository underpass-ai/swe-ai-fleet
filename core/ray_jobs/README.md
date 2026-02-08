# Core Ray Jobs

Execution payload and adapters used by Ray workers for agent task execution.

## Scope

`core/ray_jobs` includes:

- Domain entities for agent config, requests, prompts, and results
- Application use cases:
  - `ExecuteAgentTask`
  - `GenerateProposal`
- Ports for result publishing, LLM access, and async execution
- Infrastructure adapters:
  - `RayAgentExecutor`
  - `VLLMHTTPClient`
  - `NATSResultPublisher`
  - `AsyncioExecutor`

## Event Publishing

`NATSResultPublisher` publishes EventEnvelope-wrapped agent responses, including:

- `agent.response.completed`
- `agent.response.completed.task-extraction`
- `agent.response.completed.backlog-review.role`
- failure counterparts via the same domain flow

This is the key bridge between Ray workers and downstream services (Planning, processors, Orchestrator).

## Integration

Primary consumer:

- `services/ray_executor`

## Tests

```bash
make test-module MODULE=core/ray_jobs
```
