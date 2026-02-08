# Core Ceremony Engine

Reusable ceremony execution engine based on declarative YAML definitions.

## Scope

`core/ceremony_engine` contains:

- Domain model for ceremony definitions and instances
- Value objects for states, transitions, steps, guards, retries, and outputs
- Application services and use cases:
  - `CeremonyRunner`
  - `SubmitDeliberationUseCase`
  - `SubmitTaskExtractionUseCase`
  - `RehydrationUseCase`
- Ports for persistence, messaging, definition loading, step handlers, and metrics
- Infrastructure adapters for Neo4j/Valkey/NATS and YAML validation/mapping

## Step Handling

Step handlers are registered through `StepHandlerRegistry` and executed by `CeremonyRunner`.
Implemented handler families include deliberation, task extraction, publish, aggregation, and human-gate steps.

## Primary Consumer

- `services/planning_ceremony_processor`

## Tests

```bash
make test-module MODULE=core/ceremony_engine
```
