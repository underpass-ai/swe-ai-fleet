# Core Memory

Lightweight memory primitives for session event persistence and prompt context windows.

## Current Scope

`core/memory` currently includes:

- `RedisStoreImpl` in `adapters/redis_store.py`
- DTOs:
  - `LlmCallDTO`
  - `LlmResponseDTO`
- Persistence ports:
  - `PersistenceStorePort`
  - `PersistenceKvPort`
  - `PersistencePipelinePort`

Implemented store capabilities:

- Save LLM calls and responses to per-session Redis Streams
- Session metadata and TTL handling
- Retrieve recent events
- Build bounded context windows from recent events

## Implementation Status

- `cataloger.py` and `summarizer.py` are placeholders (stub behavior)
- A `.venv` directory is currently present under `core/memory/ports/.venv` and should be treated as workspace noise, not module logic

## Tests

```bash
make test-module MODULE=core/memory
```
