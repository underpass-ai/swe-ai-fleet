#!/bin/bash
# Standalone script to generate protobuf files
# Usage: ./scripts/generate-protos.sh
# Or: make generate-protos

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate virtual environment if exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
fi

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

