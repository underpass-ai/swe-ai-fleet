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

### Purge AGENT_RESPONSES only (clear old messages)

To remove all messages from the `AGENT_RESPONSES` stream (e.g. after changing message format to EventEnvelope) without deleting other streams. Uses `nats-box` image and NATS CLI (no custom image needed):

```bash
kubectl delete job nats-purge-agent-responses -n swe-ai-fleet 2>/dev/null || true
kubectl apply -f ../99-jobs/nats-purge-agent-responses.yaml
kubectl wait --for=condition=complete job/nats-purge-agent-responses -n swe-ai-fleet --timeout=60s
```

If the job fails or times out, check logs: `kubectl logs -n swe-ai-fleet job/nats-purge-agent-responses`

### Purge or inspect streams via NATS CLI (interactive)

To connect to a shell inside the cluster with the NATS CLI and purge streams manually (or inspect state):

**1. Start a temporary pod with nats-box (same namespace):**

```bash
kubectl run nats-cli -n swe-ai-fleet --rm -it --restart=Never \
  --image=docker.io/natsio/nats-box:latest -- sleep 3600
```

**2. In another terminal, open a shell in that pod:**

```bash
kubectl exec -it nats-cli -n swe-ai-fleet -- /bin/sh
```

**3. Inside the pod, set the server URL and use the CLI:**

```bash
export NATS_SERVER="nats://nats.swe-ai-fleet.svc.cluster.local:4222"

# Check JetStream
nats server check jetstream --server "$NATS_SERVER"

# List streams and message counts
nats stream ls --server "$NATS_SERVER"

# Purge one stream (removes all messages, keeps the stream)
nats stream purge AGENT_RESPONSES -f --server "$NATS_SERVER"

# Or purge all streams that typically have messages (empty everything)
nats stream purge AGENT_RESPONSES -f --server "$NATS_SERVER"
nats stream purge CONTEXT -f --server "$NATS_SERVER"
nats stream purge PLANNING_EVENTS -f --server "$NATS_SERVER"

# Verify
nats stream ls --server "$NATS_SERVER"
```

**4. Exit and clean up (if you did not use `--rm`):**

```bash
exit
kubectl delete pod nats-cli -n swe-ai-fleet
```

Streams remain; only messages are removed. To delete streams entirely, use the [Recreate Streams](#recreate-streams) procedure (nats-delete-streams job then nats-streams-init).

---

## Notes

- This job is **idempotent** - safe to run multiple times
- Existing streams are not affected
- Run after NATS upgrades or resets


