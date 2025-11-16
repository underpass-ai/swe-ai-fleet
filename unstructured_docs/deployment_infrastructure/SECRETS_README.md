# Kubernetes Secrets Management

## Overview

The file `01-secrets.yaml` contains sensitive credentials and is **excluded from git** (`.gitignore`).

## Secrets Included

| Secret Name | Purpose | Keys |
|-------------|---------|------|
| `neo4j-auth` | Neo4j database credentials | `NEO4J_USER`, `NEO4J_PASSWORD` |
| `huggingface-token` | HuggingFace API token for vLLM | `HF_TOKEN` |
| `grafana-admin` | Grafana admin credentials | `admin-user`, `admin-password` |

**TLS Secrets** (auto-managed by cert-manager, not included):
- `grafana-tls`, `monitoring-tls`, `nats-tls`, `po-ui-tls`, etc.

---

## Recreating Secrets

### Option 1: Export from Existing Cluster

If you have access to a working cluster:

```bash
#!/bin/bash
NAMESPACE="swe-ai-fleet"
OUTPUT="deploy/k8s/01-secrets.yaml"

# Export secrets (excluding TLS)
SECRETS=("neo4j-auth" "huggingface-token" "grafana-admin")

cat > "$OUTPUT" << 'HEADER'
---
# WARNING: This file contains sensitive data and is excluded from git.
HEADER

for secret in "${SECRETS[@]}"; do
  kubectl get secret "${secret}" -n "${NAMESPACE}" -o yaml | \
    grep -v "creationTimestamp:\|resourceVersion:\|uid:\|selfLink:\|managedFields:" >> "$OUTPUT"
  echo "---" >> "$OUTPUT"
done
```

### Option 2: Create from Scratch

If setting up a new environment:

```bash
# Neo4j credentials
kubectl create secret generic neo4j-auth \
  --from-literal=NEO4J_USER=neo4j \
  --from-literal=NEO4J_PASSWORD=YOUR_SECURE_PASSWORD \
  -n swe-ai-fleet

# HuggingFace token (get from https://huggingface.co/settings/tokens)
kubectl create secret generic huggingface-token \
  --from-literal=HF_TOKEN=hf_YOUR_TOKEN_HERE \
  -n swe-ai-fleet

# Grafana admin credentials
kubectl create secret generic grafana-admin \
  --from-literal=admin-user=admin \
  --from-literal=admin-password=YOUR_ADMIN_PASSWORD \
  -n swe-ai-fleet
```

---

## Security Best Practices

1. ✅ **Never commit** `01-secrets.yaml` to git (already in `.gitignore`)
2. ✅ **Rotate passwords** regularly (especially Neo4j, Grafana)
3. ✅ **Use strong passwords** (minimum 16 characters, alphanumeric + symbols)
4. ✅ **Limit access** to this file (production secrets should use sealed-secrets or vault)
5. ✅ **Document** how to recreate secrets (this file)

---

## Applying Secrets

```bash
# Apply secrets to cluster
kubectl apply -f deploy/k8s/01-secrets.yaml

# Verify secrets exist
kubectl get secrets -n swe-ai-fleet | grep -E "neo4j-auth|huggingface-token|grafana-admin"
```

---

## Troubleshooting

### Secret Not Found

```bash
# Check if secret exists
kubectl get secret <secret-name> -n swe-ai-fleet

# View secret data (base64 encoded)
kubectl get secret <secret-name> -n swe-ai-fleet -o yaml

# Decode a specific key
kubectl get secret neo4j-auth -n swe-ai-fleet -o jsonpath='{.data.NEO4J_PASSWORD}' | base64 -d
```

### Updating Secrets

```bash
# Delete and recreate
kubectl delete secret <secret-name> -n swe-ai-fleet
kubectl create secret generic <secret-name> --from-literal=KEY=VALUE -n swe-ai-fleet

# Or edit in place (opens in editor)
kubectl edit secret <secret-name> -n swe-ai-fleet
```

### Pods Not Seeing Updated Secrets

```bash
# Restart pods to pick up new secret values
kubectl rollout restart deployment/<deployment-name> -n swe-ai-fleet
```

---

## Production Deployment

For production environments, consider:

1. **Sealed Secrets** (Bitnami): Encrypt secrets for git storage
   - https://github.com/bitnami-labs/sealed-secrets

2. **External Secrets Operator**: Sync from AWS Secrets Manager, Vault, etc.
   - https://external-secrets.io/

3. **SOPS** (Mozilla): Encrypt YAML files with GPG/KMS
   - https://github.com/mozilla/sops

4. **HashiCorp Vault**: Enterprise secret management
   - https://www.vaultproject.io/docs/platform/k8s

---

## Last Updated

- **Date**: 2025-11-08
- **Cluster**: wrx80-node1 (Arch Linux, K8s v1.34.1)
- **Namespace**: swe-ai-fleet

