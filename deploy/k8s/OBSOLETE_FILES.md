# Obsolete Files - DO NOT USE

**Date**: 2025-11-08
**Reason**: Directory reorganization - files migrated to subdirectories

---

## Files to DELETE (after verification)

### Confirmed Obsolete

| File | Reason | Migrated To |
|------|--------|-------------|
| `04-services.yaml` | Frankenstein file (4 services mixed) | Individual files in 30-microservices/ |
| `07-neo4j-secret.yaml` | Duplicate of 01-secrets.yaml | 01-secrets.yaml |

### Legacy Numbered Files (ALL)

All numbered files (`01-`, `02-`, `03-`, etc.) in root `deploy/k8s/` are **legacy**.

**New structure uses subdirectories**:
- `00-foundation/`
- `10-infrastructure/`
- `20-streams/`
- `30-microservices/`
- `40-monitoring/`
- `50-ingress/`
- `90-debug/`
- `99-jobs/`

---

## Deletion Plan

### Phase 1: Backup

```bash
mkdir -p .skip/backup-deploy-$(date +%Y%m%d)
cp deploy/k8s/*.yaml .skip/backup-deploy-$(date +%Y%m%d)/
```

### Phase 2: Delete Confirmed Obsolete

```bash
git rm deploy/k8s/04-services.yaml
git rm deploy/k8s/07-neo4j-secret.yaml
```

### Phase 3: Delete Legacy Numbered Files (after testing new structure)

```bash
# Only delete after confirming new structure works
git rm deploy/k8s/0*.yaml
git rm deploy/k8s/1*.yaml
git rm deploy/k8s/2*.yaml
git rm deploy/k8s/3*.yaml
git rm deploy/k8s/vllm-server.yaml
```

---

## Verification Before Deletion

```bash
# 1. Test new structure deploys correctly
cd scripts/infra
./deploy-organized.sh --verify

# 2. Verify all pods running
kubectl get pods -n swe-ai-fleet

# 3. ONLY THEN delete legacy files
```

---

## Notes

- **Keep `01-secrets.yaml`** in root (gitignored, not committed)
- **Keep READMEs** (CONTEXT_DEPLOYMENT.md, SECRETS_README.md, etc.)
- Legacy files remain until new structure is verified in production
