# E2E Test: Workspace Kafka Offset Replay

This test validates Kafka consume offset contract and replay modes.

## What it verifies

1. Catalog exposes `kafka.produce`, `kafka.consume`, `kafka.topic_metadata`.
2. `kafka.produce` enforces approval (`approval_required`).
3. Topic allowlist deny (`policy_denied`) for disallowed topics.
4. Input validation errors (`invalid_argument`) for:
   - `offset_mode=absolute` without `offset`
   - `offset_mode=timestamp` without `timestamp_ms`
5. Replay contract with produced markers:
   - `offset_mode=timestamp` finds produced messages from time window.
   - `offset_mode=absolute` replays from exact offset.
   - `offset_mode=earliest|latest` return consistent mode outputs.

## Runtime requirements

- Ephemeral dependencies stack up (`e2e-kafka`).

## Build and push

```bash
cd e2e/tests/40-workspace-kafka-offset-replay
make build-push
```

## Deploy and inspect

```bash
make deploy
make status
make logs
make delete
```

## Evidence output

- The test writes JSON evidence to `EVIDENCE_FILE`.
- The same JSON is emitted in logs between:
  - `EVIDENCE_JSON_START`
  - `EVIDENCE_JSON_END`
