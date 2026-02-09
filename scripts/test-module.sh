#!/bin/bash
# Test a specific module
# Usage: ./scripts/test-module.sh <module-path> [pytest-args...]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <module-path> [pytest-args...]"
    echo "Example: $0 core/shared -v"
    exit 1
fi

MODULE_PATH="$1"
shift
PYTEST_ARGS="$@"

cd "$PROJECT_ROOT"

if [ ! -f "$MODULE_PATH/pyproject.toml" ]; then
    echo "❌ Error: $MODULE_PATH/pyproject.toml not found"
    exit 1
fi

echo "🧪 Testing module: $MODULE_PATH"
echo ""

# Select Python interpreter.
PYTHON_BIN="${PYTHON:-python}"
REQUIRES_PYTHON=$(grep -E '^requires-python = ' "$MODULE_PATH/pyproject.toml" | sed 's/requires-python = "\(.*\)"/\1/' || true)
if [[ "$REQUIRES_PYTHON" == *"<3.12"* ]]; then
    CURRENT_MINOR="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    if [ "$CURRENT_MINOR" != "3.11" ]; then
        if command -v python3.11 >/dev/null 2>&1 && python3.11 -V >/dev/null 2>&1; then
            PYTHON_BIN="python3.11"
        elif command -v pyenv >/dev/null 2>&1; then
            PY311_VER="$(pyenv versions --bare | grep -E '^3\.11(\.|$)' | head -n 1 || true)"
            if [ -n "$PY311_VER" ]; then
                PY311_BIN="$(pyenv root)/versions/$PY311_VER/bin/python"
                if [ -x "$PY311_BIN" ]; then
                    PYTHON_BIN="$PY311_BIN"
                else
                    echo "❌ Found pyenv 3.11 version ($PY311_VER) but python binary is missing: $PY311_BIN"
                    exit 1
                fi
            else
                echo "❌ $MODULE_PATH requires Python 3.11, but no 3.11 version is installed in pyenv"
                exit 1
            fi
        else
            echo "❌ $MODULE_PATH requires Python 3.11, but python3.11 is not available"
            exit 1
        fi
        echo "🐍 Using Python 3.11 for $MODULE_PATH ($PYTHON_BIN)"
    fi
fi

PIP_CMD="$PYTHON_BIN -m pip"
PYTEST_CMD="$PYTHON_BIN -m pytest"

# Select constraints based on the selected interpreter.
PY_MINOR="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
CONSTRAINTS_FILE="$PROJECT_ROOT/constraints.txt"
if [ "$PY_MINOR" = "3.11" ]; then
    CONSTRAINTS_FILE="$PROJECT_ROOT/constraints-py311.txt"
fi
if [ ! -f "$CONSTRAINTS_FILE" ]; then
    echo "❌ Constraints file not found: $CONSTRAINTS_FILE"
    exit 1
fi

# Install the module if not already installed (with dev dependencies for pytest)
MODULE_NAME=$(grep -E '^name = ' "$MODULE_PATH/pyproject.toml" | sed 's/name = "\(.*\)"/\1/')
if ! $PIP_CMD show "$MODULE_NAME" > /dev/null 2>&1; then
    echo "📦 Installing module with dev dependencies..."
    $PIP_CMD install -c "$CONSTRAINTS_FILE" -e "$MODULE_PATH[dev]" || {
        echo "❌ Failed to install $MODULE_PATH"
        exit 1
    }
else
    # Ensure dev dependencies are installed even if module is already installed
    echo "📦 Ensuring dev dependencies are installed..."
    $PIP_CMD install -c "$CONSTRAINTS_FILE" -e "$MODULE_PATH[dev]"
fi

# Generate protobuf files if the module has a generate-protos script
GENERATED_PROTOS=false
if [ -f "$MODULE_PATH/generate-protos.sh" ]; then
    echo "📌 Ensuring protobuf toolchain is installed (grpcio-tools)..."
    $PIP_CMD install -c "$CONSTRAINTS_FILE" grpcio-tools

    echo "📦 Generating protobuf files..."
    bash "$MODULE_PATH/generate-protos.sh"
    GENERATED_PROTOS=true
fi

# Setup cleanup trap - will run on exit (success or failure)
cleanup_protobuf_files() {
    if [ "$GENERATED_PROTOS" = "true" ] && [ -d "$MODULE_PATH/gen" ]; then
        echo ""
        echo "🧹 Cleaning up generated protobuf files..."
        rm -rf "$MODULE_PATH/gen"
        echo "✅ Cleanup completed"
    fi
}
trap cleanup_protobuf_files EXIT INT TERM

# Inject CEREMONIES_DIR for planning_ceremony_processor (path comes from config/env)
if [ "$MODULE_PATH" = "services/planning_ceremony_processor" ]; then
    export CEREMONIES_DIR="$PROJECT_ROOT/config/ceremonies"
fi

# Run tests
cd "$MODULE_PATH"
# Add current directory to PYTHONPATH so imports work
export PYTHONPATH="$PROJECT_ROOT:$MODULE_PATH:$PYTHONPATH"

# Generate JUnit XML report for test failure analysis
# Use a unique filename based on module path to avoid conflicts
JUNIT_XML_FILE="$PROJECT_ROOT/.test-results-$(echo "$MODULE_PATH" | tr '/' '-').xml"
mkdir -p "$(dirname "$JUNIT_XML_FILE")"

# Use eval to properly handle arguments with spaces
# Add --junit-xml to capture test results for failure analysis
eval "$PYTEST_CMD $PYTEST_ARGS --junit-xml=\"$JUNIT_XML_FILE\""
TEST_EXIT_CODE=$?

# Pytest exit code 5 means "no tests collected" - treat as success for modules without tests
if [ $TEST_EXIT_CODE -eq 5 ]; then
    echo "ℹ️  No tests found in $MODULE_PATH (exit code 5) - treating as success"
    TEST_EXIT_CODE=0
fi

# Cleanup will run automatically via trap
exit $TEST_EXIT_CODE
