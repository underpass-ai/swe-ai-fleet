#!/usr/bin/env bash
# Thin wrapper around fresh-redeploy-v2.sh with stable subcommands for Makefile.
# Usage:
#   scripts/infra/deploy.sh list-services
#   scripts/infra/deploy.sh all --fresh|--fast [--with-e2e]
#   scripts/infra/deploy.sh service <name> --fresh|--fast|--skip-build

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
    local mode="--fresh"
    local with_e2e=false

    while [ $# -gt 0 ]; do
        case "$1" in
            --fast|--fresh)
                mode="$1"
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

    bash "$DEPLOY_SCRIPT" "$mode"

    if [ "$with_e2e" = true ]; then
        bash "$E2E_SCRIPT" build-push
    fi
}

run_deploy_service() {
    if [ $# -lt 2 ]; then
        echo "Usage: $0 service <name> <--fresh|--fast|--skip-build>" >&2
        exit 1
    fi

    local service="$1"
    shift

    case "${1:-}" in
        --fresh|--fast|--skip-build)
            bash "$DEPLOY_SCRIPT" --service "$service" "$1"
            ;;
        *)
            echo "ERROR: service mode must be one of --fresh, --fast, --skip-build" >&2
            exit 1
            ;;
    esac
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
        echo "  all --fresh|--fast [--with-e2e]"
        echo "  service <name> --fresh|--fast|--skip-build"
        ;;
    *)
        echo "ERROR: unknown command '$COMMAND'" >&2
        exit 1
        ;;
esac
