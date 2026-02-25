#!/usr/bin/env bash
# Prune E2E job image tags in the registry, keeping only the latest N tags per image.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PRUNE_SCRIPT="${PROJECT_ROOT}/scripts/infra/prune-registry-images.sh"
E2E_TESTS_DIR="${PROJECT_ROOT}/e2e/tests"

KEEP="${KEEP:-2}"
DRY_RUN="$(echo "${DRY_RUN:-0}" | tr '[:upper:]' '[:lower:]')"
REGISTRY="${REGISTRY:-registry.underpassai.com/swe-ai-fleet}"

usage() {
    cat <<'EOF'
Usage: prune-images.sh [OPTIONS]

Options:
  --keep <N>        Number of tags to keep per image (default: 2).
  --dry-run         Print actions without deleting.
  --registry <uri>  Registry/repository prefix (default: registry.underpassai.com/swe-ai-fleet).
  -h, --help        Show this help.
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

mapfile -t REPOS < <(
    find "${E2E_TESTS_DIR}" -mindepth 1 -maxdepth 1 -type d | sort | while read -r test_dir; do
        makefile="${test_dir}/Makefile"
        [ -f "${makefile}" ] || continue
        image_name="$(sed -nE 's/^[[:space:]]*IMAGE_NAME[[:space:]]*[:?]?=[[:space:]]*([^[:space:]]+).*/\1/p' "${makefile}" | head -n 1)"
        [ -z "${image_name}" ] && continue
        echo "${REGISTRY}/${image_name}"
    done | awk '!seen[$0]++'
)

if [ "${#REPOS[@]}" -eq 0 ]; then
    echo "No E2E image repositories found under ${E2E_TESTS_DIR}."
    exit 0
fi

PRUNE_ARGS=(--keep "${KEEP}")
if [ "${DRY_RUN}" = "1" ] || [ "${DRY_RUN}" = "true" ]; then
    PRUNE_ARGS+=(--dry-run)
fi
if [ -n "${REGISTRY_AUTH_FILE:-}" ]; then
    PRUNE_ARGS+=(--registry-auth-file "${REGISTRY_AUTH_FILE}")
fi

printf '%s\n' "${REPOS[@]}" | bash "${PRUNE_SCRIPT}" "${PRUNE_ARGS[@]}"
