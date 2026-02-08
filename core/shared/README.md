# Core Shared

Shared kernel with cross-cutting value objects, event envelope contracts, and idempotency primitives.

## Scope

`core/shared` includes:

- RBAC action model:
  - `Action`
  - `ActionEnum`
  - `ScopeEnum`
  - `ACTION_SCOPES`
- Event envelope model and utilities:
  - `EventEnvelope`
  - `create_event_envelope`
  - `EventEnvelopeMapper`
  - strict parser `parse_required_envelope`
- Idempotency building blocks:
  - `IdempotencyPort`
  - `IdempotencyState`
  - `ValkeyIdempotencyAdapter`
  - middleware decorator `idempotent_consumer`
- Shared value objects reused across modules (task derivation config, task attributes, content primitives)

## Why This Module Exists

It centralizes contracts and primitives that must remain consistent across services and core contexts.
Most services import at least one part of this module for envelope parsing or idempotency safety.

## Tests

```bash
make test-module MODULE=core/shared
```
