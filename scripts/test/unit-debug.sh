#!/bin/bash
# Run unit tests in DEBUG mode
# - Extra verbose output (-vv)
# - No output capture (-s)
# - No coverage collection
# - Show full tracebacks (--tb=long)
# Usage: ./scripts/test/unit-debug.sh [pytest args]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔧 Preparing test environment (DEBUG MODE)..."
echo ""

# Activate virtual environment (if exists)
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "ℹ️  No .venv found (CI environment assumed)"
fi

# Generate protobuf files (NOT committed to repo)
echo ""
source "$SCRIPT_DIR/_generate_protos.sh"
generate_protobuf_files

# Setup cleanup trap - will run on exit (success or failure)
trap cleanup_protobuf_files EXIT INT TERM

# Run unit tests in DEBUG mode
echo ""
echo "🐛 Running unit tests in DEBUG MODE..."
echo "   - Extra verbose (-vv)"
echo "   - No output capture (-s)"
echo "   - No coverage collection"
echo "   - Full tracebacks (--tb=long)"
echo ""

# Default args if none provided
if [ $# -eq 0 ]; then
    # Run all unit tests with debug flags
    pytest -m 'not e2e and not integration' \
        -vv \
        -s \
        --tb=long \
        --color=yes \
        tests/unit/ \
        services/orchestrator/tests/ \
        services/monitoring/tests/ \
        services/planning/tests/unit/
else
    # Run with custom args but add debug flags
    pytest -vv -s --tb=long --color=yes "$@"
fi

TEST_EXIT_CODE=$?

# Show result
echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All tests passed in DEBUG mode!"
else
    echo "❌ Some tests failed (exit code: $TEST_EXIT_CODE)"
fi

# Cleanup will run automatically via trap
exit $TEST_EXIT_CODE

