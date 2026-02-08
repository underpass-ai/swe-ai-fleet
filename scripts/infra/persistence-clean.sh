#!/usr/bin/env bash
# Run the one-shot persistence cleanup Kubernetes job.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NAMESPACE="${NAMESPACE:-swe-ai-fleet}"
JOB_NAME="${JOB_NAME:-persistence-cleanup-all}"
MANIFEST_PATH="${MANIFEST_PATH:-$PROJECT_ROOT/deploy/k8s/99-jobs/persistence-cleanup-all.yaml}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-300s}"
TAIL_LINES="${TAIL_LINES:-200}"

if [ ! -f "$MANIFEST_PATH" ]; then
    echo "ERROR: manifest not found: $MANIFEST_PATH" >&2
    exit 1
fi

echo "Running persistence cleanup job..."
echo "Namespace: $NAMESPACE"
echo "Job: $JOB_NAME"
echo "Manifest: $MANIFEST_PATH"

kubectl delete job -n "$NAMESPACE" "$JOB_NAME" >/dev/null 2>&1 || true
kubectl apply -f "$MANIFEST_PATH"
kubectl wait --for=condition=complete "job/$JOB_NAME" -n "$NAMESPACE" --timeout="$WAIT_TIMEOUT"
kubectl logs -n "$NAMESPACE" "job/$JOB_NAME" --tail="$TAIL_LINES"

echo "Persistence cleanup completed."
