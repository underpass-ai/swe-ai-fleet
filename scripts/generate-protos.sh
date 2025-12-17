#!/bin/bash
# Standalone script to generate protobuf files
# Usage: ./scripts/generate-protos.sh
# Or: make generate-protos

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Select constraints based on the running interpreter.
PY_MINOR="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
CONSTRAINTS_FILE="$PROJECT_ROOT/constraints.txt"
if [ "$PY_MINOR" = "3.11" ]; then
    CONSTRAINTS_FILE="$PROJECT_ROOT/constraints-py311.txt"
fi

if [ ! -f "$CONSTRAINTS_FILE" ]; then
    echo "❌ Constraints file not found: $CONSTRAINTS_FILE"
    exit 1
fi

# Activate virtual environment if exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
fi

# Ensure grpcio-tools is available for generation.
pip install -c "$CONSTRAINTS_FILE" grpcio-tools

# Source the shared function
source "$SCRIPT_DIR/test/_generate_protos.sh"

# Generate protobuf files
generate_protobuf_files

echo ""
echo "✅ Protobuf generation complete!"
echo ""
echo "📝 Generated files are in:"
echo "   - services/orchestrator/gen/"
echo "   - services/context/gen/"
echo "   - services/planning/gen/"
echo "   - services/task_derivation/gen/"
echo ""
echo "💡 To clean generated files, run: make clean-protos"
echo "💡 Or: source scripts/test/_generate_protos.sh && cleanup_protobuf_files"

