#!/bin/bash
# Run unit tests with automatic protobuf generation
# Usage: ./scripts/test/unit.sh [pytest args]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

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
echo "📦 Generating protobuf files for all modules..."
for module in services/orchestrator services/context services/planning services/task_derivation services/ray_executor services/workflow services/backlog_review_processor; do
    if [ -f "$module/generate-protos.sh" ]; then
        echo "  Generating protos for $module..."
        bash "$module/generate-protos.sh" || true
    fi
done

# Setup cleanup trap - will run on exit (success or failure)
cleanup_protobuf_files() {
    echo ""
    echo "🧹 Cleaning up generated protobuf files..."
    for module in services/orchestrator services/context services/planning services/task_derivation services/ray_executor services/workflow services/backlog_review_processor; do
        if [ -d "$module/gen" ]; then
            rm -rf "$module/gen"
        fi
    done
    echo "✅ Cleanup completed"
}
trap cleanup_protobuf_files EXIT INT TERM

# Run unit tests
echo ""
echo "🧪 Running unit tests..."
echo ""

# Default args if none provided
if [ $# -eq 0 ]; then
    # Run core module tests individually
    echo "📦 Running core module tests..."
    CORE_MODULES=(
        "core/shared"
        "core/memory"
        "core/context"
        "core/orchestrator"
        "core/agents_and_tools"
        "core/ray_jobs"
        "core/reports"
    )

    CORE_EXIT=0
    for module in "${CORE_MODULES[@]}"; do
        if [ -f "$module/pyproject.toml" ] && [ -d "$module/tests" ] || find "$module" -name "test_*.py" -o -name "*_test.py" | grep -q .; then
            echo ""
            echo "  Testing $module..."
            cd "$module"
            pytest -m 'not e2e and not integration' \
                --cov="$module" \
                --cov-branch \
                --cov-report= \
                -v \
                --tb=short \
                . || CORE_EXIT=$?
            cd "$PROJECT_ROOT"
        fi
    done

    # Run service module tests individually
    echo ""
    echo "🔧 Running service module tests..."
    SERVICE_MODULES=(
        "services/backlog_review_processor"
        "services/context"
        "services/orchestrator"
        "services/planning"
        "services/ray_executor"
        "services/task_derivation"
        "services/workflow"
    )

    SERVICES_EXIT=0
    for module in "${SERVICE_MODULES[@]}"; do
        if [ -f "$module/pyproject.toml" ] && [ -d "$module/tests" ] || find "$module" -name "test_*.py" -o -name "*_test.py" | grep -q .; then
            echo ""
            echo "  Testing $module..."
            cd "$module"
            pytest -m 'not e2e and not integration' \
                --cov="$module" \
                --cov-branch \
                --cov-report= \
                -v \
                --tb=short \
                . || SERVICES_EXIT=$?
            cd "$PROJECT_ROOT"
        fi
    done

    # Combine coverage from all modules and generate reports
    echo ""
    echo "📊 Combining coverage reports..."
    cd "$PROJECT_ROOT"
    coverage combine || true

    # Generate coverage.xml with relative paths for SonarQube
    echo "📊 Generating coverage.xml for SonarQube..."
    coverage xml -o coverage.xml
    # Fix source path to be relative (SonarQube requirement)
    # Coverage.py writes absolute paths, but SonarQube needs relative paths
    python3 << 'EOF'
import xml.etree.ElementTree as ET
import os

# Read coverage.xml
tree = ET.parse('coverage.xml')
root = tree.getroot()

# Fix all source paths to be relative
for source in root.findall('.//sources/source'):
    if source.text and os.path.isabs(source.text):
        source.text = '.'

# Write back
tree.write('coverage.xml', encoding='utf-8', xml_declaration=True)
print("✅ Fixed coverage.xml source paths to relative (.)")
EOF

    # Generate HTML and JSON reports
    coverage html -d htmlcov
    coverage json -o coverage.json

    # Check for failures and report which test suites failed
    FAILED_SERVICES=()
    if [ $CORE_EXIT -ne 0 ]; then
        FAILED_SERVICES+=("Core modules")
    fi
    if [ $SERVICES_EXIT -ne 0 ]; then
        FAILED_SERVICES+=("Service modules")
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

