# 99-jobs - Utility Jobs

## Purpose

One-time or maintenance jobs for system initialization and cleanup.

**Run as needed** - Not part of normal deployment flow.

---

## Jobs

| File | Purpose | When to Run |
|------|---------|-------------|
| `nats-delete-streams.yaml` | Delete all NATS JetStream streams | Before clean slate reset |
| `orchestrator-delete-councils.yaml` | Delete all deliberation councils | Before fresh init |
| `orchestrator-init-councils.yaml` | Initialize default councils | First time setup |
| `deliberation-trigger.yaml` | Manually trigger a deliberation | Testing/debugging |

---

## Usage

### Clean NATS Streams

```bash
# 1. Delete existing streams
kubectl apply -f nats-delete-streams.yaml
kubectl wait --for=condition=complete job/nats-delete-streams -n swe-ai-fleet --timeout=30s

# 2. Recreate streams
kubectl apply -f ../20-streams/nats-streams-init.yaml
kubectl wait --for=condition=complete job/nats-streams-init -n swe-ai-fleet --timeout=60s
```

---

### Reset Orchestrator Councils

```bash
# 1. Delete existing councils
kubectl apply -f orchestrator-delete-councils.yaml
kubectl wait --for=condition=complete job/orchestrator-delete-councils -n swe-ai-fleet --timeout=30s

# 2. Initialize default councils
kubectl apply -f orchestrator-init-councils.yaml
kubectl wait --for=condition=complete job/orchestrator-init-councils -n swe-ai-fleet --timeout=60s
```

---

### Trigger Manual Deliberation

```bash
# For testing only
kubectl apply -f deliberation-trigger.yaml

# Check logs
kubectl logs -n swe-ai-fleet job/deliberation-trigger --follow
```

---

## Job Cleanup

Jobs remain in cluster after completion. Clean up periodically:

```bash
# Delete completed jobs
kubectl delete job -n swe-ai-fleet --field-selector status.successful=1

# Or specific job
kubectl delete job nats-delete-streams -n swe-ai-fleet
```

---

## Notes

- Jobs are **idempotent** where possible
- Always check logs after completion: `kubectl logs job/<name> -n swe-ai-fleet`
- Failed jobs remain for debugging - delete manually after investigation

