#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DOCKERFILE="${PROJECT_ROOT}/services/workspace/runner-images/Dockerfile"
REGISTRY="${REGISTRY:-registry.underpassai.com/swe-ai-fleet}"
TAG="${TAG:-v0.1.0}"

PROFILES=(base toolchains secops container k6 fat)
ACTION=""
PROFILE="all"
NO_CACHE=false
TAG_LATEST=false

usage() {
    cat <<EOF
Usage:
  $0 <list|build|push|build-push> [--profile <name>|all] [--tag <tag>] [--registry <registry>] [--no-cache] [--tag-latest]

Examples:
  $0 list
  $0 build --profile toolchains --tag v0.1.0
  $0 build-push --profile all --tag v0.1.0 --registry registry.underpassai.com/swe-ai-fleet

Profiles:
  base | toolchains | secops | container | k6 | fat | all
EOF
}

if [ $# -lt 1 ]; then
    usage
    exit 1
fi

ACTION="$1"
shift

while [ $# -gt 0 ]; do
    case "$1" in
        --profile)
            PROFILE="${2:-}"
            shift 2
            ;;
        --tag)
            TAG="${2:-}"
            shift 2
            ;;
        --registry)
            REGISTRY="${2:-}"
            shift 2
            ;;
        --no-cache)
            NO_CACHE=true
            shift
            ;;
        --tag-latest)
            TAG_LATEST=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: unknown argument: $1" >&2
            usage
            exit 1
            ;;
    esac
done

if [ ! -f "$DOCKERFILE" ]; then
    echo "ERROR: Dockerfile not found: $DOCKERFILE" >&2
    exit 1
fi

profile_exists() {
    local target="$1"
    for p in "${PROFILES[@]}"; do
        if [ "$p" = "$target" ]; then
            return 0
        fi
    done
    return 1
}

resolve_profiles() {
    if [ "$PROFILE" = "all" ]; then
        printf '%s\n' "${PROFILES[@]}"
        return
    fi
    if ! profile_exists "$PROFILE"; then
        echo "ERROR: invalid profile '$PROFILE'" >&2
        exit 1
    fi
    printf '%s\n' "$PROFILE"
}

image_ref() {
    local p="$1"
    echo "${REGISTRY}/workspace-runner-${p}:${TAG}"
}

image_ref_latest() {
    local p="$1"
    echo "${REGISTRY}/workspace-runner-${p}:latest"
}

build_profile() {
    local p="$1"
    local image
    image="$(image_ref "$p")"

    echo "Building ${image} (target=${p})"
    local -a args
    args=(build -f "$DOCKERFILE" --target "$p" -t "$image")
    if [ "$TAG_LATEST" = true ]; then
        args+=(-t "$(image_ref_latest "$p")")
    fi
    if [ "$NO_CACHE" = true ]; then
        args+=(--no-cache)
    fi
    args+=("$PROJECT_ROOT")
    podman "${args[@]}"
}

push_profile() {
    local p="$1"
    local image
    image="$(image_ref "$p")"
    echo "Pushing ${image}"
    podman push "$image"
    if [ "$TAG_LATEST" = true ]; then
        local latest_image
        latest_image="$(image_ref_latest "$p")"
        echo "Pushing ${latest_image}"
        podman push "$latest_image"
    fi
}

list_profiles() {
    echo "Runner image profiles:"
    for p in "${PROFILES[@]}"; do
        echo "  - ${p}: $(image_ref "$p")"
    done
}

mapfile -t SELECTED_PROFILES < <(resolve_profiles)

case "$ACTION" in
    list)
        list_profiles
        ;;
    build)
        for p in "${SELECTED_PROFILES[@]}"; do
            build_profile "$p"
        done
        ;;
    push)
        for p in "${SELECTED_PROFILES[@]}"; do
            push_profile "$p"
        done
        ;;
    build-push)
        for p in "${SELECTED_PROFILES[@]}"; do
            build_profile "$p"
            push_profile "$p"
        done
        ;;
    *)
        echo "ERROR: unknown action '$ACTION'" >&2
        usage
        exit 1
        ;;
esac

echo "Runner image action '${ACTION}' completed."
