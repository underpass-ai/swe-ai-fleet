#!/bin/bash
# Run unit tests with automatic protobuf generation
# Usage: ./scripts/test/unit.sh [pytest args]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔧 Preparing test environment..."
echo ""

# Activate virtual environment (if exists - optional in CI)
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "ℹ️  No .venv found (CI environment assumed)"
    # CI installs packages globally via 'make install-deps'
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
    # Run core tests first
    echo "📦 Running core tests..."
    pytest -m 'not e2e and not integration' \
        --cov=core \
        --cov-branch \
        --cov-report=term-missing \
        --cov-report=xml \
        --cov-report=html \
        --cov-report=json \
        -v \
        --tb=short \
        tests/unit/

    CORE_EXIT=$?

    # Run each service's tests independently to avoid conftest namespace collisions
    echo ""
    echo "🔧 Running Orchestrator tests..."
    pytest -m 'not e2e and not integration' \
        --cov=services/orchestrator \
        --cov-append \
        --cov-branch \
        --cov-report= \
        -v \
        --tb=short \
        services/orchestrator/tests/

    ORCH_EXIT=$?

    echo ""
    echo "📊 Running Monitoring tests..."
    pytest -m 'not e2e and not integration' \
        --cov=services/monitoring \
        --cov-append \
        --cov-branch \
        --cov-report= \
        -v \
        --tb=short \
        services/monitoring/tests/

    MON_EXIT=$?

    echo ""
    echo "📅 Running Planning tests..."
    pytest -m 'not e2e and not integration' \
        --cov=services/planning \
        --cov-append \
        --cov-branch \
        --cov-report= \
        -v \
        --tb=short \
        services/planning/tests/unit/

    PLAN_EXIT=$?

    # Generate final combined reports
    echo ""
    echo "📈 Generating combined coverage reports..."
    python -m coverage report --skip-covered
    python -m coverage html
    python -m coverage xml
    python -m coverage json

    # Return non-zero if any test suite failed
    if [ $CORE_EXIT -ne 0 ] || [ $ORCH_EXIT -ne 0 ] || [ $MON_EXIT -ne 0 ] || [ $PLAN_EXIT -ne 0 ]; then
        exit 1
    fi
else
    pytest "$@"
fi

TEST_EXIT_CODE=$?

# Show result
echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All unit tests passed! Coverage report:"
    echo "   📊 Terminal: see above"
    echo "   📄 XML: coverage.xml"
    echo "   🌐 HTML: htmlcov/index.html"
else
    echo "❌ Some tests failed (exit code: $TEST_EXIT_CODE)"
fi

# Cleanup will run automatically via trap
exit $TEST_EXIT_CODE

