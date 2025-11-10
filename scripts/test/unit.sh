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
    # Run all core tests (both locations for backward compatibility)
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
        core/agents_and_tools/tests/unit/ \
        tests/unit/core/

    CORE_EXIT=$?
    CORE_OTHER_EXIT=0  # Already included above

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

    echo ""
    echo "🔄 Running Workflow tests..."
    pytest -m 'not e2e and not integration' \
        --cov=services/workflow \
        --cov-append \
        --cov-branch \
        --cov-report= \
        -v \
        --tb=short \
        services/workflow/tests/unit/

    WORKFLOW_EXIT=$?

    echo ""
    echo "🔀 Running Context Service tests..."
    pytest -m 'not e2e and not integration' \
        --cov=services/context \
        --cov-append \
        --cov-branch \
        --cov-report= \
        -v \
        --tb=short \
        tests/unit/services/context/

    CONTEXT_EXIT=$?

    echo ""
    echo "⚡ Running Ray Executor tests..."
    pytest -m 'not e2e and not integration' \
        --cov=services/ray_executor \
        --cov-append \
        --cov-branch \
        --cov-report= \
        -v \
        --tb=short \
        tests/unit/services/ray_executor/

    RAY_EXIT=$?

    # Generate final combined reports
    echo ""
    echo "📈 Generating combined coverage reports..."

    # In CI: only XML for SonarQube (minimal)
    # Local: full reports for debugging
    if [ -n "$CI" ]; then
        echo "🔧 CI mode: generating coverage.xml only"
        python -m coverage xml
    else
        echo "💻 Local mode: generating all reports"
        python -m coverage report --skip-covered
        python -m coverage html
        python -m coverage xml
        python -m coverage json
    fi

    # Check for failures and report which services failed
    FAILED_SERVICES=()
    if [ $CORE_EXIT -ne 0 ]; then
        FAILED_SERVICES+=("Core")
    fi
    if [ $CORE_OTHER_EXIT -ne 0 ]; then
        FAILED_SERVICES+=("Core (other)")
    fi
    if [ $ORCH_EXIT -ne 0 ]; then
        FAILED_SERVICES+=("Orchestrator")
    fi
    if [ $MON_EXIT -ne 0 ]; then
        FAILED_SERVICES+=("Monitoring")
    fi
    if [ $PLAN_EXIT -ne 0 ]; then
        FAILED_SERVICES+=("Planning")
    fi
    if [ $WORKFLOW_EXIT -ne 0 ]; then
        FAILED_SERVICES+=("Workflow")
    fi
    if [ $CONTEXT_EXIT -ne 0 ]; then
        FAILED_SERVICES+=("Context")
    fi
    if [ $RAY_EXIT -ne 0 ]; then
        FAILED_SERVICES+=("Ray Executor")
    fi

    # Return non-zero if any test suite failed
    if [ ${#FAILED_SERVICES[@]} -gt 0 ]; then
        echo ""
        echo "❌ Tests failed in the following services:"
        for service in "${FAILED_SERVICES[@]}"; do
            echo "   - $service"
        done
        echo ""
        echo "💡 Tip: Scroll up to see detailed error messages from pytest"
        echo "💡 Or run tests for a specific service:"
        echo "   pytest services/<service>/tests/unit/ -v"
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

