#!/usr/bin/env bash
# Remove generated protobuf stubs (gen/) for every module that declares generate-protos.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# shellcheck source=scripts/lib/modules.sh
source "$PROJECT_ROOT/scripts/lib/modules.sh"

cd "$PROJECT_ROOT"

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    echo "Usage: $0"
    echo ""
    echo "Removes generated gen/ folders for modules with generate-protos.sh."
    exit 0
fi

mapfile -t PROTO_MODULES < <(list_proto_modules)
if [ "${#PROTO_MODULES[@]}" -eq 0 ]; then
    echo "No modules with generate-protos.sh were found."
    exit 0
fi

echo "Cleaning generated protobuf folders..."
for module in "${PROTO_MODULES[@]}"; do
    if [ -d "$PROJECT_ROOT/$module/gen" ]; then
        echo "- removing $module/gen"
        rm -rf "$PROJECT_ROOT/$module/gen"
    fi
done

echo "Protobuf cleanup completed."
