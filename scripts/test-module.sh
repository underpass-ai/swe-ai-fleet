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

# Install the module if not already installed (with dev dependencies for pytest)
MODULE_NAME=$(grep -E '^name = ' "$MODULE_PATH/pyproject.toml" | sed 's/name = "\(.*\)"/\1/')
if ! pip show "$MODULE_NAME" > /dev/null 2>&1; then
    echo "📦 Installing module with dev dependencies..."
    pip install -e "$MODULE_PATH[dev]" || {
        echo "❌ Failed to install $MODULE_PATH"
        exit 1
    }
else
    # Ensure dev dependencies are installed even if module is already installed
    echo "📦 Ensuring dev dependencies are installed..."
    pip install -e "$MODULE_PATH[dev]" || {
        echo "⚠️  Warning: Failed to install dev dependencies, continuing with existing installation..."
    }
fi

# Generate protobuf files if the module has a generate-protos script
GENERATED_PROTOS=false
if [ -f "$MODULE_PATH/generate-protos.sh" ]; then
    echo "📦 Generating protobuf files..."
    bash "$MODULE_PATH/generate-protos.sh" || {
        echo "⚠️  Warning: Failed to generate protos, continuing anyway..."
    }
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

# Run tests (exclude integration tests by default unless explicitly requested)
cd "$MODULE_PATH"
# Add current directory to PYTHONPATH so imports work
export PYTHONPATH="$PROJECT_ROOT:$MODULE_PATH:$PYTHONPATH"

# If no marker is specified, exclude integration tests
if [[ "$PYTEST_ARGS" != *"-m"* ]] && [[ "$PYTEST_ARGS" != *"--markers"* ]]; then
    PYTEST_ARGS="-m 'not integration' $PYTEST_ARGS"
fi

# Use eval to properly handle the marker expression with spaces
eval "pytest $PYTEST_ARGS"
TEST_EXIT_CODE=$?

# Cleanup will run automatically via trap
exit $TEST_EXIT_CODE

