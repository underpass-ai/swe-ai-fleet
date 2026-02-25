#!/usr/bin/env bash
# Clear cluster runtime state for E2E/ops:
# - delete jobs
# - clean Valkey + Neo4j + NATS (via persistence-clean job)
# - clean MinIO workspace buckets

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
NAMESPACE="${NAMESPACE:-swe-ai-fleet}"

DELETE_JOBS="${DELETE_JOBS:-true}"
CLEAR_PERSISTENCE="${CLEAR_PERSISTENCE:-true}"
CLEAR_MINIO="${CLEAR_MINIO:-true}"

MINIO_NAMESPACE="${MINIO_NAMESPACE:-$NAMESPACE}"
MINIO_SECRET_NAME="${MINIO_SECRET_NAME:-minio-workspace-app-creds}"
MINIO_ENDPOINT="${MINIO_ENDPOINT:-http://minio-workspace-svc.${MINIO_NAMESPACE}.svc.cluster.local:9000}"
MINIO_BUCKETS="${MINIO_BUCKETS:-swe-workspaces,swe-workspaces-cache,swe-workspaces-meta}"
MINIO_CLEAR_JOB_TIMEOUT="${MINIO_CLEAR_JOB_TIMEOUT:-300s}"

normalize_bool() {
    case "$(echo "${1:-}" | tr '[:upper:]' '[:lower:]')" in
        true|1|yes|y|on)
            echo "true"
            ;;
        *)
            echo "false"
            ;;
    esac
}

DELETE_JOBS="$(normalize_bool "${DELETE_JOBS}")"
CLEAR_PERSISTENCE="$(normalize_bool "${CLEAR_PERSISTENCE}")"
CLEAR_MINIO="$(normalize_bool "${CLEAR_MINIO}")"

echo "Cluster clear configuration:"
echo "  Namespace: ${NAMESPACE}"
echo "  Delete Jobs: ${DELETE_JOBS}"
echo "  Clear Persistence (Valkey/Neo4j/NATS): ${CLEAR_PERSISTENCE}"
echo "  Clear MinIO: ${CLEAR_MINIO}"
echo ""

if [[ "${DELETE_JOBS}" == "true" ]]; then
    echo "Deleting jobs in namespace ${NAMESPACE}..."
    kubectl delete job -n "${NAMESPACE}" --all --ignore-not-found=true >/dev/null
    echo "Jobs deleted."
    echo ""
fi

if [[ "${CLEAR_PERSISTENCE}" == "true" ]]; then
    echo "Running persistence cleanup (Valkey/Neo4j/NATS)..."
    NAMESPACE="${NAMESPACE}" bash "${PROJECT_ROOT}/scripts/infra/persistence-clean.sh"
    echo ""
fi

if [[ "${CLEAR_MINIO}" == "true" ]]; then
    if ! kubectl get secret -n "${MINIO_NAMESPACE}" "${MINIO_SECRET_NAME}" >/dev/null 2>&1; then
        echo "WARNING: MinIO secret ${MINIO_NAMESPACE}/${MINIO_SECRET_NAME} not found. Skipping MinIO cleanup."
    else
        echo "Running MinIO cleanup for buckets: ${MINIO_BUCKETS}"
        MINIO_CLEAR_JOB="minio-workspace-clear-$(date +%s)"
        TMP_MANIFEST="/tmp/${MINIO_CLEAR_JOB}.yaml"

        cat > "${TMP_MANIFEST}" <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: ${MINIO_CLEAR_JOB}
  namespace: ${MINIO_NAMESPACE}
spec:
  ttlSecondsAfterFinished: 300
  backoffLimit: 1
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: clear-minio
        image: docker.io/minio/mc:latest
        imagePullPolicy: IfNotPresent
        env:
        - name: MINIO_ENDPOINT
          value: "${MINIO_ENDPOINT}"
        - name: MINIO_BUCKETS
          value: "${MINIO_BUCKETS}"
        - name: MINIO_ACCESS_KEY
          valueFrom:
            secretKeyRef:
              name: ${MINIO_SECRET_NAME}
              key: accessKey
        - name: MINIO_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: ${MINIO_SECRET_NAME}
              key: secretKey
        command:
        - /bin/sh
        - -ec
        - |
          mc alias set ws "\${MINIO_ENDPOINT}" "\${MINIO_ACCESS_KEY}" "\${MINIO_SECRET_KEY}"
          for bucket in swe-workspaces swe-workspaces-cache swe-workspaces-meta; do
            echo "Clearing bucket \${bucket}..."
            if mc ls "ws/\${bucket}" >/dev/null 2>&1; then
              mc rm --recursive --force "ws/\${bucket}" || true
            else
              echo "Bucket \${bucket} does not exist, skipping"
            fi
          done
          echo "MinIO cleanup completed."
EOF

        kubectl delete job -n "${MINIO_NAMESPACE}" "${MINIO_CLEAR_JOB}" --ignore-not-found=true >/dev/null
        kubectl apply -f "${TMP_MANIFEST}" >/dev/null
        if kubectl wait -n "${MINIO_NAMESPACE}" --for=condition=complete "job/${MINIO_CLEAR_JOB}" --timeout="${MINIO_CLEAR_JOB_TIMEOUT}" 2>/dev/null; then
            echo "MinIO cleanup job completed."
        else
            echo "WARNING: MinIO cleanup job did not complete. Checking status..."
            kubectl get job -n "${MINIO_NAMESPACE}" "${MINIO_CLEAR_JOB}" -o wide 2>/dev/null || true
        fi
        kubectl logs -n "${MINIO_NAMESPACE}" "job/${MINIO_CLEAR_JOB}" --tail=200 2>/dev/null || true
        rm -f "${TMP_MANIFEST}"
        echo ""
    fi
fi

echo "Cluster clear completed."
