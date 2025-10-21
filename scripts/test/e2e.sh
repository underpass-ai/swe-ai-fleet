#!/bin/bash
# Run E2E tests
# Usage: ./scripts/test/e2e.sh [pytest args]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Running E2E tests..."
echo ""

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "❌ Error: .venv not found"
    exit 1
fi

# Generate protobuf files (NOT committed to repo)
echo ""
source "$SCRIPT_DIR/_generate_protos.sh"
generate_protobuf_files

# Setup cleanup trap - will run on exit (success or failure)
trap cleanup_protobuf_files EXIT INT TERM

# Run E2E tests
echo ""
echo "🧪 Running E2E tests..."
echo ""

if [ $# -eq 0 ]; then
    pytest tests/e2e/ -m e2e -v --tb=short
else
    pytest "$@"
fi

TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All E2E tests passed!"
else
    echo "❌ Some E2E tests failed (exit code: $TEST_EXIT_CODE)"
fi

# Cleanup will run automatically via trap
exit $TEST_EXIT_CODE

