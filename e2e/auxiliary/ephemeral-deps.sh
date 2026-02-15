#!/usr/bin/env bash
# Ephemeral dependencies for Workspace E2E governance tests.
# Deploys MongoDB, PostgreSQL, Kafka (Redpanda), RabbitMQ and NATS,
# runs lightweight bootstrap jobs, and tears everything down on demand.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST="${SCRIPT_DIR}/ephemeral-deps.yaml"
NAMESPACE="${NAMESPACE:-swe-ai-fleet}"

ACTION="${1:-}"
shift || true

while [[ $# -gt 0 ]]; do
    case "$1" in
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

usage() {
    cat <<EOF
Usage:
  $0 up [--namespace <ns>]
  $0 down [--namespace <ns>]
  $0 status [--namespace <ns>]
EOF
}

wait_deployments() {
    local deployments=(
        e2e-mongodb
        e2e-postgres
        e2e-nats
        e2e-rabbitmq
        e2e-kafka
    )
    for deploy in "${deployments[@]}"; do
        kubectl rollout status -n "${NAMESPACE}" "deployment/${deploy}" --timeout=240s
    done
}

wait_jobs() {
    local jobs=(
        e2e-ephemeral-kafka-init
        e2e-ephemeral-rabbit-init
        e2e-ephemeral-mongo-seed
    )
    for job in "${jobs[@]}"; do
        kubectl wait -n "${NAMESPACE}" --for=condition=complete "job/${job}" --timeout=240s
    done
}

delete_bootstrap_jobs() {
    kubectl delete job -n "${NAMESPACE}" \
        e2e-ephemeral-kafka-init \
        e2e-ephemeral-rabbit-init \
        e2e-ephemeral-mongo-seed \
        --ignore-not-found=true >/dev/null
}

case "${ACTION}" in
    up)
        delete_bootstrap_jobs
        kubectl apply -f "${MANIFEST}" >/dev/null
        wait_deployments
        wait_jobs
        echo "Ephemeral dependencies are ready in namespace ${NAMESPACE}."
        ;;
    down)
        kubectl delete -f "${MANIFEST}" --ignore-not-found=true >/dev/null
        echo "Ephemeral dependencies deleted from namespace ${NAMESPACE}."
        ;;
    status)
        kubectl get deploy,svc,job,pod -n "${NAMESPACE}" -l e2e.underpass.ai/component=ephemeral-deps
        ;;
    *)
        usage
        exit 1
        ;;
esac
