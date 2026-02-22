# MinIO Workspace Store

Object store dedicated to workspace data (workspaces, artifacts, caches, metadata).

## Files

- `00-namespace.yaml`
- `00-secrets.example.yaml` (template only)
- `01-pvc.yaml`
- `02-minio-deployment.yaml`
- `03-minio-service.yaml`
- `04-minio-ingress.yaml` (optional)
- `05-minio-bootstrap-job.yaml`
- `06-workspace-gc-cronjob.yaml`
- `07-networkpolicies.yaml` (recommended)
- `configmaps/minio-bootstrap.sh`
- `configmaps/workspace-gc.sh`
- `apply.sh`

## Buckets

- `swe-workspaces`
- `swe-workspaces-cache`
- `swe-workspaces-meta`

## Deploy

### Option A: one-command deploy (recommended)

```bash
./deploy/minio-workspace/apply.sh
```

Override GC policy/schedule and optional resources:

```bash
WORKSPACE_GC_SCHEDULE="0 */6 * * *" \
WORKSPACE_GC_RETENTION_DAYS="14" \
WORKSPACE_GC_BUCKET="swe-workspaces" \
WORKSPACE_GC_PREFIX="sessions/" \
MINIO_WORKSPACE_APPLY_INGRESS="false" \
MINIO_WORKSPACE_APPLY_NETWORKPOLICY="true" \
./deploy/minio-workspace/apply.sh
```

### Option B: step-by-step apply

1. Create namespace and storage.

```bash
kubectl apply -f deploy/minio-workspace/00-namespace.yaml
kubectl apply -f deploy/minio-workspace/01-pvc.yaml
```

2. Create secrets (use your real values; do not apply the example as-is).

```bash
# review template
cat deploy/minio-workspace/00-secrets.example.yaml

# apply your edited secrets file
kubectl apply -f <your-secrets-file>.yaml
```

3. Deploy MinIO.

```bash
kubectl apply -f deploy/minio-workspace/02-minio-deployment.yaml
kubectl apply -f deploy/minio-workspace/03-minio-service.yaml
# optional ingress
kubectl apply -f deploy/minio-workspace/04-minio-ingress.yaml
```

AWS public DNS option:

- Keep ingress optional by default.
- If you expose MinIO publicly on AWS, set your host and add ingress controller annotations (ALB/NLB + external-dns) according to your cluster standard.
- Keep MinIO API private unless there is a strict requirement for public exposure.

4. Create script ConfigMaps from source scripts.

```bash
kubectl create configmap minio-workspace-bootstrap-scripts \
  -n swe-ai-fleet \
  --from-file=minio-bootstrap.sh=deploy/minio-workspace/configmaps/minio-bootstrap.sh \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create configmap workspace-gc-scripts \
  -n swe-ai-fleet \
  --from-file=workspace-gc.sh=deploy/minio-workspace/configmaps/workspace-gc.sh \
  --dry-run=client -o yaml | kubectl apply -f -
```

5. Run bootstrap job.

```bash
kubectl apply -f deploy/minio-workspace/05-minio-bootstrap-job.yaml
kubectl wait --for=condition=complete job/minio-workspace-bootstrap -n swe-ai-fleet --timeout=180s
kubectl logs -n swe-ai-fleet job/minio-workspace-bootstrap
```

6. Enable GC cronjob.

```bash
kubectl apply -f deploy/minio-workspace/06-workspace-gc-cronjob.yaml
kubectl get cronjob -n swe-ai-fleet workspace-gc
```

7. Apply network policy (recommended).

```bash
kubectl apply -f deploy/minio-workspace/07-networkpolicies.yaml
```

8. Allow selected namespaces to reach MinIO.

```bash
kubectl label namespace swe-ai-fleet access-minio-workspace=true --overwrite
```

## Parameterization

### GC retention days

Set `WORKSPACE_GC_RETENTION_DAYS` when running `apply.sh`, or edit `RETENTION_DAYS` in `06-workspace-gc-cronjob.yaml`.

### GC schedule

Set `WORKSPACE_GC_SCHEDULE` when running `apply.sh`, or edit `spec.schedule` in `06-workspace-gc-cronjob.yaml`.

### One-off dry run

```bash
kubectl create job --from=cronjob/workspace-gc workspace-gc-manual -n swe-ai-fleet
kubectl set env job/workspace-gc-manual -n swe-ai-fleet GC_DRY_RUN=true
kubectl logs -f -n swe-ai-fleet job/workspace-gc-manual
```

## Verify bootstrap results

```bash
kubectl run -it --rm mc-check --restart=Never -n swe-ai-fleet \
  --image=docker.io/minio/mc:latest -- /bin/sh

mc alias set ws http://minio-workspace-svc.swe-ai-fleet.svc.cluster.local:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
mc ls ws
```

## Notes

- Root credentials (`minio-workspace-root`) and app credentials (`minio-workspace-app-creds`) are intentionally separate.
- Bootstrap is idempotent and can be re-run after script/policy changes.
- GC script prefers `mc + jq` strict timestamp filtering and falls back to `mc find --older-than` if `jq` is unavailable in the runtime image.
