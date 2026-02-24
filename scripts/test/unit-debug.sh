#!/bin/bash
# Run unit tests in DEBUG mode
# - Extra verbose output (-vv)
# - No output capture (-s)
# - No coverage collection
# - Show full tracebacks (--tb=long)
# Usage: ./scripts/test/unit-debug.sh [pytest args]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "Preparing test environment (DEBUG MODE)..."
echo ""

# Activate virtual environment (if exists)
if [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$PROJECT_ROOT/.venv/bin/activate"
    echo "Virtual environment activated"
else
    echo "No .venv found (CI environment assumed)"
fi

# Generate protobuf files using the canonical generation script
echo ""
echo "Generating protobuf files..."
bash "$PROJECT_ROOT/scripts/protos/generate-all.sh"

# Setup cleanup trap — remove generated protos on exit
cleanup() {
    echo ""
    echo "Cleaning up generated protobuf files..."
    bash "$PROJECT_ROOT/scripts/protos/clean-all.sh"
}
trap cleanup EXIT INT TERM

# Run unit tests in DEBUG mode
echo ""
echo "Running unit tests in DEBUG MODE..."
echo "   - Extra verbose (-vv)"
echo "   - No output capture (-s)"
echo "   - No coverage collection"
echo "   - Full tracebacks (--tb=long)"
echo ""

cd "$PROJECT_ROOT"

# Default args if none provided
if [ $# -eq 0 ]; then
    pytest -vv -s --tb=long --color=yes .
else
    pytest -vv -s --tb=long --color=yes "$@"
fi

TEST_EXIT_CODE=$?

echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "All tests passed in DEBUG mode!"
else
    echo "Some tests failed (exit code: $TEST_EXIT_CODE)"
fi

# Cleanup will run automatically via trap
exit $TEST_EXIT_CODE
