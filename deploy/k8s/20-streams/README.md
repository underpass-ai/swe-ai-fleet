# 20-streams - NATS JetStream Initialization

## Purpose

Initialize NATS JetStream streams required by all microservices.

**Apply third** - After infrastructure is ready, before microservices.

---

## Files

| File | Resource | Purpose |
|------|----------|---------|
| `nats-streams-init.yaml` | Job | Creates JetStream streams and consumers |

---

## Streams Created

| Stream | Subjects | Purpose |
|--------|----------|---------|
| `planning-events` | `planning.story.>` | Story lifecycle events |
| `workflow-events` | `workflow.task.>` | Task state transitions |
| `agent-requests` | `agent.work.>` | Agent task assignments |
| `agent-results` | `agent.results.>` | Agent execution results |
| `context-updates` | `context.updated` | Context change notifications |

---

## Apply

```bash
# Delete old job if exists
kubectl delete job nats-streams-init -n swe-ai-fleet 2>/dev/null || true

# Apply
kubectl apply -f nats-streams-init.yaml

# Wait for completion (60s timeout)
kubectl wait --for=condition=complete job/nats-streams-init -n swe-ai-fleet --timeout=60s
```

---

## Dependencies

**Requires**:
- ✅ NATS StatefulSet running (`10-infrastructure/nats.yaml`)
- ✅ NATS ready and accepting connections

---

## Verification

```bash
# Check job completed
kubectl get job nats-streams-init -n swe-ai-fleet

# Check job logs
kubectl logs -n swe-ai-fleet job/nats-streams-init

# Expected output: "✅ All streams created successfully"
```

---

## Troubleshooting

### Job Failed

```bash
# Check logs for errors
kubectl logs -n swe-ai-fleet job/nats-streams-init --previous

# Common issues:
# - NATS not ready yet → Wait for NATS StatefulSet
# - Connection refused → Check NATS service
# - Timeout → Increase job timeout in YAML
```

### Recreate Streams

```bash
# Use nats-delete-streams job first (99-jobs/)
kubectl apply -f ../99-jobs/nats-delete-streams.yaml
kubectl wait --for=condition=complete job/nats-delete-streams -n swe-ai-fleet --timeout=30s

# Then recreate
kubectl apply -f nats-streams-init.yaml
```

---

## Notes

- This job is **idempotent** - safe to run multiple times
- Existing streams are not affected
- Run after NATS upgrades or resets

