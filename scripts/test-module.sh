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

# Select constraints based on the running interpreter.
PY_MINOR="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
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
if ! pip show "$MODULE_NAME" > /dev/null 2>&1; then
    echo "📦 Installing module with dev dependencies..."
    pip install -c "$CONSTRAINTS_FILE" -e "$MODULE_PATH[dev]" || {
        echo "❌ Failed to install $MODULE_PATH"
        exit 1
    }
else
    # Ensure dev dependencies are installed even if module is already installed
    echo "📦 Ensuring dev dependencies are installed..."
    pip install -c "$CONSTRAINTS_FILE" -e "$MODULE_PATH[dev]"
fi

# Generate protobuf files if the module has a generate-protos script
GENERATED_PROTOS=false
if [ -f "$MODULE_PATH/generate-protos.sh" ]; then
    echo "📌 Ensuring protobuf toolchain is installed (grpcio-tools)..."
    pip install -c "$CONSTRAINTS_FILE" grpcio-tools

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

# Run tests
cd "$MODULE_PATH"
# Add current directory to PYTHONPATH so imports work
export PYTHONPATH="$PROJECT_ROOT:$MODULE_PATH:$PYTHONPATH"

# Use eval to properly handle arguments with spaces
eval "pytest $PYTEST_ARGS"
TEST_EXIT_CODE=$?

# Cleanup will run automatically via trap
exit $TEST_EXIT_CODE

