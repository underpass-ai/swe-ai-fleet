#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${MINIO_WORKSPACE_NAMESPACE:-minio-workspace}"
GC_SCHEDULE="${WORKSPACE_GC_SCHEDULE:-0 4 * * *}"
GC_RETENTION_DAYS="${WORKSPACE_GC_RETENTION_DAYS:-7}"
GC_BUCKET="${WORKSPACE_GC_BUCKET:-swe-workspaces}"
GC_PREFIX="${WORKSPACE_GC_PREFIX:-sessions/}"
APPLY_INGRESS="${MINIO_WORKSPACE_APPLY_INGRESS:-false}"
APPLY_NETWORKPOLICY="${MINIO_WORKSPACE_APPLY_NETWORKPOLICY:-true}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Applying MinIO workspace resources in namespace=${NAMESPACE}"

kubectl apply -f "${ROOT_DIR}/00-namespace.yaml"
kubectl apply -f "${ROOT_DIR}/01-pvc.yaml"
kubectl apply -f "${ROOT_DIR}/02-minio-deployment.yaml"
kubectl apply -f "${ROOT_DIR}/03-minio-service.yaml"

if [[ "${APPLY_INGRESS}" == "true" ]]; then
  kubectl apply -f "${ROOT_DIR}/04-minio-ingress.yaml"
fi

kubectl create configmap minio-workspace-bootstrap-scripts \
  -n "${NAMESPACE}" \
  --from-file=minio-bootstrap.sh="${ROOT_DIR}/configmaps/minio-bootstrap.sh" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create configmap workspace-gc-scripts \
  -n "${NAMESPACE}" \
  --from-file=workspace-gc.sh="${ROOT_DIR}/configmaps/workspace-gc.sh" \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f "${ROOT_DIR}/05-minio-bootstrap-job.yaml"
kubectl wait --for=condition=complete job/minio-workspace-bootstrap -n "${NAMESPACE}" --timeout=180s

kubectl apply -f "${ROOT_DIR}/06-workspace-gc-cronjob.yaml"
kubectl set env cronjob/workspace-gc -n "${NAMESPACE}" \
  BUCKET="${GC_BUCKET}" \
  PREFIX="${GC_PREFIX}" \
  RETENTION_DAYS="${GC_RETENTION_DAYS}" \
  --containers=gc
kubectl patch cronjob workspace-gc -n "${NAMESPACE}" --type merge \
  -p "$(printf '{\"spec\":{\"schedule\":\"%s\"}}' "${GC_SCHEDULE}")"

if [[ "${APPLY_NETWORKPOLICY}" == "true" ]]; then
  kubectl apply -f "${ROOT_DIR}/07-networkpolicies.yaml"
fi

echo "Done."
echo "GC schedule: ${GC_SCHEDULE}"
echo "GC retention days: ${GC_RETENTION_DAYS}"
