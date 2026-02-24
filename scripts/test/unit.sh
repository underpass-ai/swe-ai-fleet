#!/usr/bin/env bash
# Run unit tests across modules with per-module execution and consolidated coverage.
# Usage: ./scripts/test/unit.sh [pytest args]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# shellcheck source=scripts/lib/modules.sh
source "$PROJECT_ROOT/scripts/lib/modules.sh"

cd "$PROJECT_ROOT"

cleanup_junit_xml() {
    rm -f "$PROJECT_ROOT/.test-results-"*.xml 2>/dev/null || true
}
trap cleanup_junit_xml EXIT INT TERM

activate_venv_if_present() {
    if [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
        # shellcheck disable=SC1091
        source "$PROJECT_ROOT/.venv/bin/activate"
        echo "Virtual environment activated"
    else
        echo "No .venv found; continuing with current Python environment"
    fi
}

run_module_suite() {
    local suite_name="$1"
    shift
    local suite_exit=0

    echo "Running ${suite_name}..."

    local module
    for module in "$@"; do
        if [ ! -f "$module/pyproject.toml" ]; then
            echo "- skip $module (no pyproject.toml)"
            continue
        fi
        if ! module_has_tests "$module"; then
            echo "- skip $module (no tests)"
            continue
        fi

        echo "- test $module"
        "$PROJECT_ROOT/scripts/test/test-module.sh" "$module" --cov-report=xml || suite_exit=$?
    done

    return "$suite_exit"
}

run_ray_suite() {
    local py_minor="$1"
    local ray_exit=0

    if [ "$py_minor" = "3.11" ]; then
        echo "Running Ray modules locally (Python 3.11 detected)..."
        "$PROJECT_ROOT/scripts/test/test-module.sh" "core/ray_jobs" --cov-report=xml || ray_exit=$?
        "$PROJECT_ROOT/scripts/test/test-module.sh" "services/ray_executor" --cov-report=xml || ray_exit=$?
    else
        echo "Running Ray modules in containerized Python 3.11..."
        bash "$PROJECT_ROOT/scripts/test/local-docker.sh" "core/ray_jobs" --cov-report=xml || ray_exit=$?
        bash "$PROJECT_ROOT/scripts/test/local-docker.sh" "services/ray_executor" --cov-report=xml || ray_exit=$?
    fi

    return "$ray_exit"
}

combine_and_normalize_coverage() {
    echo "Combining coverage reports..."
    python3 "$PROJECT_ROOT/scripts/test/combine_coverage_xml.py" "$PROJECT_ROOT" "$PROJECT_ROOT/coverage.xml" || true

    if [ -f "$PROJECT_ROOT/coverage.xml" ]; then
        python3 "$PROJECT_ROOT/scripts/test/normalize_coverage_xml.py" "$PROJECT_ROOT/coverage.xml"
    else
        echo "WARN: coverage.xml was not generated"
    fi

    if [ -f "$PROJECT_ROOT/.coverage" ]; then
        coverage html -d "$PROJECT_ROOT/htmlcov" 2>/dev/null || echo "WARN: could not generate HTML coverage"
        coverage json -o "$PROJECT_ROOT/coverage.json" 2>/dev/null || echo "WARN: could not generate JSON coverage"
    elif [ ! -f "$PROJECT_ROOT/coverage.json" ]; then
        echo '{"meta": {"version": "7.13.0"}, "files": {}}' > "$PROJECT_ROOT/coverage.json"
    fi
}

print_failure_summary() {
    echo ""
    echo "Detailed test failure summary:"
    python3 "$PROJECT_ROOT/scripts/test/summarize_junit_failures.py" "$PROJECT_ROOT" || true
    echo ""
    echo "Tip: run focused tests with make test-module MODULE=<module-path>"
}

activate_venv_if_present

if [ $# -gt 0 ]; then
    pytest "$@"
    exit $?
fi

PY_MINOR="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"

CORE_EXIT=0
SERVICES_EXIT=0
RAY_EXIT=0

if [ "$PY_MINOR" = "3.11" ]; then
    echo "Python 3.11 detected: skipping non-Ray module suites (require Python >= 3.13)"
else
    run_module_suite "core modules" "${CORE_MODULES_PY313[@]}" || CORE_EXIT=$?
    run_module_suite "service modules" "${SERVICE_MODULES_PY313[@]}" || SERVICES_EXIT=$?
fi

run_ray_suite "$PY_MINOR" || RAY_EXIT=$?

combine_and_normalize_coverage

FAILED_GROUPS=()
if [ "$CORE_EXIT" -ne 0 ]; then
    FAILED_GROUPS+=("core modules")
fi
if [ "$SERVICES_EXIT" -ne 0 ]; then
    FAILED_GROUPS+=("service modules")
fi
if [ "$RAY_EXIT" -ne 0 ]; then
    FAILED_GROUPS+=("ray modules")
fi

if [ "${#FAILED_GROUPS[@]}" -gt 0 ]; then
    echo ""
    echo "Tests failed in:"
    printf ' - %s\n' "${FAILED_GROUPS[@]}"
    print_failure_summary
    exit 1
fi

echo ""
echo "All unit test suites passed."
[ -f "$PROJECT_ROOT/coverage.xml" ] && echo "coverage.xml generated"
[ -f "$PROJECT_ROOT/coverage.json" ] && echo "coverage.json generated"
