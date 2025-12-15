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

# Run unit tests
echo ""
echo "🧪 Running unit tests..."
echo ""

# Default args if none provided
if [ $# -eq 0 ]; then
    PY_MINOR="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

    # Run core module tests individually
    echo "📦 Running core module tests..."
    CORE_MODULES=(
        "core/shared"
        "core/memory"
        "core/context"
        "core/orchestrator"
        "core/agents_and_tools"
        # core/ray_jobs is Python 3.11-only; run it in the ray_executor Python 3.11 environment.
        "core/reports"
    )

    CORE_EXIT=0
    for module in "${CORE_MODULES[@]}"; do
        if [ -f "$module/pyproject.toml" ] && [ -d "$module/tests" ] || find "$module" -name "test_*.py" -o -name "*_test.py" | grep -q .; then
            echo ""
            echo "  Testing $module..."
            # Use test-module.sh which handles dev dependencies installation
            "$PROJECT_ROOT/scripts/test-module.sh" "$module" \
                --cov-report= \
                || CORE_EXIT=$?
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
        # services/ray_executor is Python 3.11-only; run it separately below.
        "services/task_derivation"
        "services/workflow"
    )

    SERVICES_EXIT=0
    for module in "${SERVICE_MODULES[@]}"; do
        if [ -f "$module/pyproject.toml" ] && [ -d "$module/tests" ] || find "$module" -name "test_*.py" -o -name "*_test.py" | grep -q .; then
            echo ""
            echo "  Testing $module..."
            # Use test-module.sh which handles dev dependencies installation
            "$PROJECT_ROOT/scripts/test-module.sh" "$module" \
                --cov-report= \
                || SERVICES_EXIT=$?
        fi
    done

    # Run Ray modules (Python 3.11) in a container if host Python is not 3.11.
    # This keeps "make test-unit" as a single entry point for the whole monorepo.
    RAY_EXIT=0
    if [ "$PY_MINOR" = "3.11" ]; then
        echo ""
        echo "🧩 Running Ray modules locally (Python 3.11 detected)..."
        "$PROJECT_ROOT/scripts/test-module.sh" "core/ray_jobs" --cov-report= || RAY_EXIT=$?
        "$PROJECT_ROOT/scripts/test-module.sh" "services/ray_executor" --cov-report= || RAY_EXIT=$?
    else
        echo ""
        echo "🧩 Running Ray modules in an isolated Python 3.11 container..."
        bash "$PROJECT_ROOT/scripts/test/local-docker.sh" "core/ray_jobs" --cov-report= || RAY_EXIT=$?
        bash "$PROJECT_ROOT/scripts/test/local-docker.sh" "services/ray_executor" --cov-report= || RAY_EXIT=$?
    fi

    # Combine coverage from all modules and generate reports
    echo ""
    echo "📊 Combining coverage reports..."
    cd "$PROJECT_ROOT"

    # Install coverage if not already installed
    pip install coverage > /dev/null 2>&1 || true

    # Find and combine all .coverage data files from modules
    # test-module.sh generates both .coverage and coverage.xml
    COVERAGE_DATA_FILES=$(find . -name ".coverage" \( -path "*/core/*" -o -path "*/services/*" \) 2>/dev/null || true)

    if [ -n "$COVERAGE_DATA_FILES" ]; then
        # Combine all .coverage files
        echo "$COVERAGE_DATA_FILES" | while read -r cov_file; do
            if [ -f "$cov_file" ]; then
                coverage combine "$cov_file" 2>/dev/null || true
            fi
        done
    fi

    # Generate coverage.xml with relative paths for SonarQube
    echo "📊 Generating coverage.xml for SonarQube..."
    if coverage xml -o coverage.xml 2>/dev/null; then
        echo "✅ Coverage report generated from combined data"
    else
        echo "⚠️  No coverage data to combine - individual module coverage.xml files remain in their directories"
        # Create a placeholder or use the first available
        FIRST_COV=$(find . -name "coverage.xml" \( -path "*/core/*" -o -path "*/services/*" \) 2>/dev/null | head -1)
        if [ -n "$FIRST_COV" ] && [ -f "$FIRST_COV" ]; then
            cp "$FIRST_COV" coverage.xml
            echo "✅ Using first available coverage.xml as fallback"
        fi
    fi
    # Fix source path to be relative (SonarQube requirement)
    if [ -f "coverage.xml" ]; then
        python3 << 'EOF'
import xml.etree.ElementTree as ET
import os

try:
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
except Exception as e:
    print(f"⚠️  Warning: Could not fix coverage.xml paths: {e}")
EOF
    fi

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
        if [ $RAY_EXIT -ne 0 ]; then
            echo "   - Ray modules (core/ray_jobs, services/ray_executor)"
        fi
        echo ""
        echo "💡 Tip: Scroll up to see detailed error messages from pytest"
        echo "💡 Or run tests for a specific module:"
        echo "   make test-module MODULE=<module-path>"
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

