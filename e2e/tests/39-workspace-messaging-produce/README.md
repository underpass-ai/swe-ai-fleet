# E2E Test: Workspace Messaging Produce

This test validates governed messaging write tools with writable profiles.

## What it verifies

1. Catalog exposes `nats.publish`, `kafka.produce`, `rabbit.publish` and their read counterparts.
2. Scope allowlists deny disallowed subjects/topics/queues (`policy_denied`).
3. Write tools enforce explicit approval (`approval_required`).
4. NATS publish is validated with concurrent `nats.subscribe_pull` marker check.
5. Kafka `produce -> consume` returns marker from consumed payloads.
6. Rabbit `publish -> consume` returns marker from consumed payloads.

## Runtime requirements

- Ephemeral dependencies stack must be up (`e2e-nats`, `e2e-kafka`, `e2e-rabbitmq`).

## Build and push

```bash
cd e2e/tests/39-workspace-messaging-produce
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
