#!/bin/bash
# Run unit tests with coverage report
# Usage: ./scripts/test/coverage.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔧 Preparing test environment with coverage..."
echo ""

# Activate virtual environment (if exists - optional in CI)
if [ -f ".venv/bin/activate" ]; then
    echo "✅ Activating local .venv"
    source .venv/bin/activate
else
    echo "ℹ️  No .venv found (CI environment assumed)"
    # CI installs packages globally, no venv needed
fi

# Generate protobuf files (NOT committed to repo)
echo ""
source "$SCRIPT_DIR/_generate_protos.sh"
generate_protobuf_files

# Setup cleanup trap - will run on exit (success or failure)
trap cleanup_protobuf_files EXIT INT TERM

# Run tests with coverage
echo ""
echo "🧪 Running tests with coverage..."
echo ""

pytest -m 'not e2e and not integration' \
    --cov=swe_ai_fleet \
    --cov=services \
    --cov-report=term-missing \
    --cov-report=xml \
    --cov-report=html \
    -v \
    --tb=short

TEST_EXIT_CODE=$?

# Show coverage summary
echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ Tests passed! Coverage report:"
    echo "   📊 Terminal: see above"
    echo "   📄 XML: coverage.xml"
    echo "   🌐 HTML: htmlcov/index.html"
else
    echo "❌ Some tests failed (exit code: $TEST_EXIT_CODE)"
fi

# Cleanup will run automatically via trap
exit $TEST_EXIT_CODE

