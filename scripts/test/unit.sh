#!/bin/bash
# Run unit tests with automatic protobuf generation
# Usage: ./scripts/test/unit.sh [pytest args]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔧 Preparing test environment..."
echo ""

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Error: .venv not found. Run: python -m venv .venv && source .venv/bin/activate && pip install -e '.[grpc,dev]'"
    exit 1
fi

# Generate protobuf files (NOT committed to repo)
echo ""
source "$SCRIPT_DIR/_generate_protos.sh"
generate_protobuf_files

# Setup cleanup trap - will run on exit (success or failure)
trap cleanup_protobuf_files EXIT INT TERM

# Run unit tests
echo ""
echo "🧪 Running unit tests..."
echo ""

# Default args if none provided
if [ $# -eq 0 ]; then
    pytest -m 'not e2e and not integration' -v --tb=short
else
    pytest "$@"
fi

TEST_EXIT_CODE=$?

# Show result
echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All unit tests passed!"
else
    echo "❌ Some tests failed (exit code: $TEST_EXIT_CODE)"
fi

# Cleanup will run automatically via trap
exit $TEST_EXIT_CODE

