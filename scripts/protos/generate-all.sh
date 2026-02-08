#!/usr/bin/env bash
# Generate protobuf stubs for every module that declares generate-protos.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# shellcheck source=scripts/lib/modules.sh
source "$PROJECT_ROOT/scripts/lib/modules.sh"

cd "$PROJECT_ROOT"

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    echo "Usage: $0"
    echo ""
    echo "Generates protobuf stubs for modules with generate-protos.sh."
    echo "On Python != 3.11, services/ray_executor is skipped because it is Python 3.11-only."
    exit 0
fi

PY_MINOR="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
CONSTRAINTS_FILE="$PROJECT_ROOT/constraints.txt"
if [ "$PY_MINOR" = "3.11" ]; then
    CONSTRAINTS_FILE="$PROJECT_ROOT/constraints-py311.txt"
fi

if [ ! -f "$CONSTRAINTS_FILE" ]; then
    echo "ERROR: constraints file not found: $CONSTRAINTS_FILE" >&2
    exit 1
fi

echo "Generating protobuf files for all modules..."
echo "Python: $PY_MINOR"
echo "Constraints: $CONSTRAINTS_FILE"

pip install -c "$CONSTRAINTS_FILE" grpcio-tools

mapfile -t PROTO_MODULES < <(list_proto_modules)
if [ "${#PROTO_MODULES[@]}" -eq 0 ]; then
    echo "No modules with generate-protos.sh were found."
    exit 0
fi

for module in "${PROTO_MODULES[@]}"; do
    if [ "$module" = "services/ray_executor" ] && [ "$PY_MINOR" != "3.11" ]; then
        echo "- skip $module (requires Python 3.11)"
        continue
    fi

    echo "- $module"
    (
        cd "$PROJECT_ROOT/$module"
        bash generate-protos.sh
    )
done

echo "Protobuf generation completed for ${#PROTO_MODULES[@]} modules."
