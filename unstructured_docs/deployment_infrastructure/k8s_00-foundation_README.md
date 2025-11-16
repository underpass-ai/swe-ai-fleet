# 00-foundation - Base Configuration

## Purpose

Foundation layer containing namespace, configuration, and secrets required before any other resources.

**Apply first** - All other resources depend on these.

---

## Files

| File | Resource | Purpose |
|------|----------|---------|
| `00-namespace.yaml` | Namespace | Creates `swe-ai-fleet` namespace |
| `00-configmaps.yaml` | 2 ConfigMaps | `service-urls` and `app-config` |
| `03-configmaps.yaml` | ConfigMap | Additional configuration (verify if needed) |

---

## Apply Order

```bash
kubectl apply -f 00-namespace.yaml
kubectl apply -f 00-configmaps.yaml
kubectl apply -f 03-configmaps.yaml  # If exists
```

---

## Secrets

**Note**: `01-secrets.yaml` is **excluded from git** (`.gitignore`)

See `deploy/k8s/SECRETS_README.md` for secrets management.

To apply secrets (if file exists):
```bash
kubectl apply -f ../01-secrets.yaml  # Lives in deploy/k8s/ root
```

---

## Dependencies

**None** - This is the foundation layer.

---

## Verification

```bash
# Verify namespace
kubectl get namespace swe-ai-fleet

# Verify ConfigMaps
kubectl get configmap -n swe-ai-fleet service-urls app-config

# Verify Secrets
kubectl get secrets -n swe-ai-fleet neo4j-auth huggingface-token grafana-admin
```

