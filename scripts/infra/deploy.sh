#!/usr/bin/env bash
# Thin wrapper around fresh-redeploy-v2.sh with stable subcommands for Makefile.
# Usage:
#   scripts/infra/deploy.sh list-services
#   scripts/infra/deploy.sh all [--cache|--no-cache] [--build-only|--skip-build] [--reset-nats] [--with-e2e]
#   scripts/infra/deploy.sh service <name> [--cache|--no-cache] [--build-only|--skip-build] [--reset-nats]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOY_SCRIPT="$SCRIPT_DIR/fresh-redeploy-v2.sh"
E2E_SCRIPT="$PROJECT_ROOT/scripts/e2e/images.sh"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <list-services|all|service> [args...]" >&2
    exit 1
fi

COMMAND="$1"
shift

run_deploy_all() {
    local mode="--cache"
    local with_e2e=false
    local build_only=false
    local skip_build=false
    local reset_nats=false

    while [ $# -gt 0 ]; do
        case "$1" in
            --cache)
                mode="--cache"
                shift
                ;;
            --no-cache)
                mode="--no-cache"
                shift
                ;;
            --fast|--fresh)
                # Backward-compatible aliases.
                mode="$1"
                shift
                ;;
            --build-only)
                build_only=true
                shift
                ;;
            --skip-build)
                skip_build=true
                shift
                ;;
            --reset-nats)
                reset_nats=true
                shift
                ;;
            --with-e2e)
                with_e2e=true
                shift
                ;;
            *)
                echo "ERROR: unknown option for 'all': $1" >&2
                exit 1
                ;;
        esac
    done

    if [ "$build_only" = true ] && [ "$skip_build" = true ]; then
        echo "ERROR: --build-only cannot be combined with --skip-build" >&2
        exit 1
    fi

    local args=("$mode")
    if [ "$build_only" = true ]; then
        args+=("--build-only")
    fi
    if [ "$skip_build" = true ]; then
        args+=("--skip-build")
    fi
    if [ "$reset_nats" = true ]; then
        args+=("--reset-nats")
    fi

    bash "$DEPLOY_SCRIPT" "${args[@]}"

    if [ "$with_e2e" = true ] && [ "$build_only" = false ] && [ "$skip_build" = false ]; then
        bash "$E2E_SCRIPT" build-push
    fi
}

run_deploy_service() {
    if [ $# -lt 1 ]; then
        echo "Usage: $0 service <name> [--cache|--no-cache] [--build-only|--skip-build] [--reset-nats]" >&2
        exit 1
    fi

    local service="$1"
    shift
    local mode="--cache"
    local build_only=false
    local skip_build=false
    local reset_nats=false

    while [ $# -gt 0 ]; do
        case "$1" in
            --cache)
                mode="--cache"
                shift
                ;;
            --no-cache)
                mode="--no-cache"
                shift
                ;;
            --fast|--fresh)
                # Backward-compatible aliases.
                mode="$1"
                shift
                ;;
            --build-only)
                build_only=true
                shift
                ;;
            --skip-build)
                skip_build=true
                shift
                ;;
            --reset-nats)
                reset_nats=true
                shift
                ;;
            *)
                echo "ERROR: unknown option for 'service': $1" >&2
                exit 1
                ;;
        esac
    done

    if [ "$build_only" = true ] && [ "$skip_build" = true ]; then
        echo "ERROR: --build-only cannot be combined with --skip-build" >&2
        exit 1
    fi

    local args=(--service "$service" "$mode")
    if [ "$build_only" = true ]; then
        args+=("--build-only")
    fi
    if [ "$skip_build" = true ]; then
        args+=("--skip-build")
    fi
    if [ "$reset_nats" = true ]; then
        args+=("--reset-nats")
    fi

    bash "$DEPLOY_SCRIPT" "${args[@]}"
}

case "$COMMAND" in
    list-services)
        bash "$DEPLOY_SCRIPT" --list-services
        ;;
    all)
        run_deploy_all "$@"
        ;;
    service)
        run_deploy_service "$@"
        ;;
    -h|--help)
        echo "Usage: $0 <list-services|all|service> [args...]"
        echo "  list-services"
        echo "  all [--cache|--no-cache] [--build-only|--skip-build] [--reset-nats] [--with-e2e]"
        echo "  service <name> [--cache|--no-cache] [--build-only|--skip-build] [--reset-nats]"
        ;;
    *)
        echo "ERROR: unknown command '$COMMAND'" >&2
        exit 1
        ;;
esac
