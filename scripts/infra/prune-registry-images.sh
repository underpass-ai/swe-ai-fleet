#!/usr/bin/env bash
# Prune container image tags from one or more repositories, keeping only the newest N tags.
#
# Usage:
#   scripts/infra/prune-registry-images.sh --repo registry/ns/image-a --repo registry/ns/image-b
#   printf '%s\n' "registry/ns/image-a" | scripts/infra/prune-registry-images.sh --keep 2

set -euo pipefail

KEEP=2
DRY_RUN=false
REGISTRY_AUTH_FILE="${REGISTRY_AUTH_FILE:-}"
declare -a REPOS=()

usage() {
    cat <<'EOF'
Usage: prune-registry-images.sh [OPTIONS]

Options:
  --repo <registry/repository>   Repository to prune (repeatable).
  --keep <N>                     Number of latest tags to keep per repository (default: 2).
  --dry-run                      Print actions without deleting.
  --registry-auth-file <path>    Auth file for skopeo operations.
  -h, --help                     Show this help.

Notes:
  - Additional repositories can be passed via stdin, one per line.
  - Tags are sorted by image Created timestamp (descending).
EOF
}

require_cmd() {
    local cmd="$1"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "ERROR: required command not found: $cmd" >&2
        exit 1
    fi
}

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

while [ $# -gt 0 ]; do
    case "$1" in
        --repo)
            if [ -z "${2:-}" ]; then
                echo "ERROR: --repo requires a value" >&2
                exit 1
            fi
            REPOS+=("$2")
            shift 2
            ;;
        --keep)
            if [ -z "${2:-}" ] || ! [[ "${2}" =~ ^[0-9]+$ ]]; then
                echo "ERROR: --keep must be an integer >= 1" >&2
                exit 1
            fi
            KEEP="${2}"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --registry-auth-file)
            if [ -z "${2:-}" ]; then
                echo "ERROR: --registry-auth-file requires a value" >&2
                exit 1
            fi
            REGISTRY_AUTH_FILE="$2"
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

if [ "${KEEP}" -lt 1 ]; then
    echo "ERROR: --keep must be >= 1" >&2
    exit 1
fi

if [ -z "${REGISTRY_AUTH_FILE}" ]; then
    if [ -f "${HOME}/.config/containers/auth.json" ]; then
        REGISTRY_AUTH_FILE="${HOME}/.config/containers/auth.json"
    elif [ -n "${XDG_RUNTIME_DIR:-}" ] && [ -f "${XDG_RUNTIME_DIR}/containers/auth.json" ]; then
        REGISTRY_AUTH_FILE="${XDG_RUNTIME_DIR}/containers/auth.json"
    fi
fi

if [ ! -t 0 ]; then
    while IFS= read -r line; do
        line="$(echo "${line}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
        [ -z "${line}" ] && continue
        REPOS+=("${line}")
    done
fi

if [ "${#REPOS[@]}" -eq 0 ]; then
    echo "ERROR: no repositories provided. Use --repo and/or stdin." >&2
    exit 1
fi

require_cmd skopeo
require_cmd jq

DRY_RUN="$(normalize_bool "${DRY_RUN}")"
declare -a AUTH_ARGS=()
if [ -n "${REGISTRY_AUTH_FILE}" ]; then
    AUTH_ARGS+=(--authfile "${REGISTRY_AUTH_FILE}")
fi

mapfile -t UNIQUE_REPOS < <(printf '%s\n' "${REPOS[@]}" | awk 'NF > 0 && !seen[$0]++')

TOTAL_REPOS=0
TOTAL_DELETED=0

prune_repo() {
    local repo="$1"
    local tags_json=""
    local tags=()
    local created=""
    local tag=""
    local idx=0
    local deleted=0
    local rows_tmp=""

    TOTAL_REPOS=$((TOTAL_REPOS + 1))
    echo "Repository: ${repo}"

    if ! tags_json="$(skopeo list-tags "${AUTH_ARGS[@]}" "docker://${repo}" 2>/dev/null)"; then
        echo "  - Skipping (repository not found or inaccessible)"
        return 0
    fi

    mapfile -t tags < <(echo "${tags_json}" | jq -r '.Tags[]?' | sed '/^$/d')
    if [ "${#tags[@]}" -le "${KEEP}" ]; then
        echo "  - Tags=${#tags[@]} (<= keep=${KEEP}), nothing to prune"
        return 0
    fi

    rows_tmp="$(mktemp)"
    for tag in "${tags[@]}"; do
        created="$(skopeo inspect "${AUTH_ARGS[@]}" --format '{{.Created}}' "docker://${repo}:${tag}" 2>/dev/null || true)"
        [ -z "${created}" ] && created="1970-01-01T00:00:00Z"
        printf '%s\t%s\n' "${created}" "${tag}" >> "${rows_tmp}"
    done

    mapfile -t SORTED_TAGS < <(sort -r "${rows_tmp}" | awk -F'\t' '{print $2}')
    rm -f "${rows_tmp}"

    for idx in "${!SORTED_TAGS[@]}"; do
        tag="${SORTED_TAGS[$idx]}"
        if [ "${idx}" -lt "${KEEP}" ]; then
            continue
        fi
        if [ "${DRY_RUN}" = "true" ]; then
            echo "  - DRY RUN delete ${repo}:${tag}"
        else
            if skopeo delete "${AUTH_ARGS[@]}" "docker://${repo}:${tag}" >/dev/null 2>&1; then
                echo "  - Deleted ${repo}:${tag}"
                deleted=$((deleted + 1))
            else
                echo "  - WARN failed to delete ${repo}:${tag}"
            fi
        fi
    done

    if [ "${DRY_RUN}" = "true" ]; then
        echo "  - DRY RUN complete"
    else
        TOTAL_DELETED=$((TOTAL_DELETED + deleted))
        echo "  - Deleted tags: ${deleted}"
    fi
}

for repo in "${UNIQUE_REPOS[@]}"; do
    prune_repo "${repo}"
done

echo ""
echo "Prune complete."
echo "Repositories processed: ${TOTAL_REPOS}"
if [ "${DRY_RUN}" = "true" ]; then
    echo "Dry run mode: no tags deleted."
else
    echo "Total tags deleted: ${TOTAL_DELETED}"
fi
