#!/usr/bin/env bash
# Prune service image tags in the registry, keeping only the latest N tags per service image.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PRUNE_SCRIPT="${PROJECT_ROOT}/scripts/infra/prune-registry-images.sh"

KEEP="${KEEP:-2}"
DRY_RUN="$(echo "${DRY_RUN:-0}" | tr '[:upper:]' '[:lower:]')"
REGISTRY="${REGISTRY:-registry.underpassai.com/swe-ai-fleet}"
SERVICE_IMAGES_CSV="${SERVICE_IMAGES:-}"

DEFAULT_SERVICE_IMAGES=(
    "orchestrator"
    "ray-executor"
    "context"
    "planning"
    "planning-ui"
    "task-derivation"
    "backlog-review-processor"
    "planning-ceremony-processor"
    "workflow"
    "workspace"
)

usage() {
    cat <<'EOF'
Usage: prune-service-images.sh [OPTIONS]

Options:
  --keep <N>            Number of tags to keep per service image (default: 2).
  --dry-run             Print actions without deleting.
  --registry <uri>      Registry/repository prefix (default: registry.underpassai.com/swe-ai-fleet).
  --service-images CSV  Override service image names (comma-separated).
  -h, --help            Show this help.
EOF
}

while [ $# -gt 0 ]; do
    case "$1" in
        --keep)
            KEEP="${2:-}"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --registry)
            REGISTRY="${2:-}"
            shift 2
            ;;
        --service-images)
            SERVICE_IMAGES_CSV="${2:-}"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

if ! [[ "${KEEP}" =~ ^[0-9]+$ ]] || [ "${KEEP}" -lt 1 ]; then
    echo "ERROR: KEEP must be an integer >= 1" >&2
    exit 1
fi

if [ ! -x "${PRUNE_SCRIPT}" ]; then
    echo "ERROR: prune helper not executable: ${PRUNE_SCRIPT}" >&2
    exit 1
fi

declare -a SERVICE_IMAGES=()
if [ -n "${SERVICE_IMAGES_CSV}" ]; then
    OLD_IFS="${IFS}"
    IFS=','
    for image in ${SERVICE_IMAGES_CSV}; do
        image="$(echo "${image}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
        [ -z "${image}" ] && continue
        SERVICE_IMAGES+=("${image}")
    done
    IFS="${OLD_IFS}"
else
    SERVICE_IMAGES=("${DEFAULT_SERVICE_IMAGES[@]}")
fi

if [ "${#SERVICE_IMAGES[@]}" -eq 0 ]; then
    echo "No service images selected."
    exit 0
fi

declare -a REPOS=()
for image in "${SERVICE_IMAGES[@]}"; do
    REPOS+=("${REGISTRY}/${image}")
done

PRUNE_ARGS=(--keep "${KEEP}")
if [ "${DRY_RUN}" = "1" ] || [ "${DRY_RUN}" = "true" ]; then
    PRUNE_ARGS+=(--dry-run)
fi
if [ -n "${REGISTRY_AUTH_FILE:-}" ]; then
    PRUNE_ARGS+=(--registry-auth-file "${REGISTRY_AUTH_FILE}")
fi

printf '%s\n' "${REPOS[@]}" | bash "${PRUNE_SCRIPT}" "${PRUNE_ARGS[@]}"
