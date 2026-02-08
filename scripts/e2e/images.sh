#!/usr/bin/env bash
# Manage E2E image build/push operations.
# Usage:
#   scripts/e2e/images.sh build [--test <test-dir>]
#   scripts/e2e/images.sh push [--test <test-dir>]
#   scripts/e2e/images.sh build-push [--test <test-dir>]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
E2E_TESTS_DIR="$PROJECT_ROOT/e2e/tests"

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    echo "Usage: $0 <build|push|build-push> [--test <test-dir>]"
    exit 0
fi

if [ $# -lt 1 ]; then
    echo "Usage: $0 <build|push|build-push> [--test <test-dir>]" >&2
    exit 1
fi

ACTION="$1"
shift

TEST_NAME=""
while [ $# -gt 0 ]; do
    case "$1" in
        --test)
            TEST_NAME="${2:-}"
            if [ -z "$TEST_NAME" ]; then
                echo "ERROR: --test requires a value" >&2
                exit 1
            fi
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 <build|push|build-push> [--test <test-dir>]"
            exit 0
            ;;
        *)
            echo "ERROR: unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

run_action_for_test() {
    local action="$1"
    local test_dir="$2"
    local test_name
    test_name="$(basename "$test_dir")"

    if [ ! -f "$test_dir/Makefile" ]; then
        echo "Skipping $test_name (no Makefile)"
        return 0
    fi

    echo "$action $test_name"
    make -C "$test_dir" "$action"
}

resolve_test_dirs() {
    if [ -n "$TEST_NAME" ]; then
        local single_dir="$E2E_TESTS_DIR/$TEST_NAME"
        if [ ! -d "$single_dir" ]; then
            echo "ERROR: test directory not found: $single_dir" >&2
            exit 1
        fi
        if [ ! -f "$single_dir/Makefile" ]; then
            echo "ERROR: $single_dir has no Makefile" >&2
            exit 1
        fi
        echo "$single_dir"
        return
    fi

    find "$E2E_TESTS_DIR" -mindepth 1 -maxdepth 1 -type d | sort
}

mapfile -t TEST_DIRS < <(resolve_test_dirs)
if [ "${#TEST_DIRS[@]}" -eq 0 ]; then
    echo "No E2E test directories found under $E2E_TESTS_DIR"
    exit 0
fi

case "$ACTION" in
    build)
        for test_dir in "${TEST_DIRS[@]}"; do
            run_action_for_test build "$test_dir"
        done
        ;;
    push)
        for test_dir in "${TEST_DIRS[@]}"; do
            run_action_for_test push "$test_dir"
        done
        ;;
    build-push)
        for test_dir in "${TEST_DIRS[@]}"; do
            run_action_for_test build "$test_dir"
            run_action_for_test push "$test_dir"
        done
        ;;
    *)
        echo "ERROR: unknown action '$ACTION'" >&2
        echo "Expected: build | push | build-push" >&2
        exit 1
        ;;
esac

echo "E2E image action '$ACTION' completed."
