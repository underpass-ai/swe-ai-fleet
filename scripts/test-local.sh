#!/bin/bash
# Run tests locally with automatic protobuf generation
# Usage: ./scripts/test-local.sh [pytest args]

set -e

echo "🔧 Preparing test environment..."
echo ""

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
else
    echo "❌ Error: .venv not found. Run: python -m venv .venv && source .venv/bin/activate && pip install -e '.[grpc,dev]'"
    exit 1
fi

# Generate context protobuf files
echo ""
echo "📦 Generating context protobuf files..."
mkdir -p services/context/gen
python -m grpc_tools.protoc \
  --proto_path=specs \
  --python_out=services/context/gen \
  --grpc_python_out=services/context/gen \
  --pyi_out=services/context/gen \
  context.proto

# Fix imports
sed -i 's/^import context_pb2/from . import context_pb2/' \
  services/context/gen/context_pb2_grpc.py

# Create __init__.py
cat > services/context/gen/__init__.py << 'EOF'
from . import context_pb2, context_pb2_grpc
__all__ = ["context_pb2", "context_pb2_grpc"]
EOF

echo "✅ Context protobuf generated"

# Generate orchestrator protobuf files
echo ""
echo "📦 Generating orchestrator protobuf files..."
mkdir -p services/orchestrator/gen
python -m grpc_tools.protoc \
  --proto_path=specs \
  --python_out=services/orchestrator/gen \
  --grpc_python_out=services/orchestrator/gen \
  --pyi_out=services/orchestrator/gen \
  orchestrator.proto

# Fix imports
sed -i 's/^import orchestrator_pb2/from . import orchestrator_pb2/' \
  services/orchestrator/gen/orchestrator_pb2_grpc.py

# Create __init__.py
cat > services/orchestrator/gen/__init__.py << 'EOF'
from . import orchestrator_pb2, orchestrator_pb2_grpc
__all__ = ["orchestrator_pb2", "orchestrator_pb2_grpc"]
EOF

echo "✅ Orchestrator protobuf generated"

# Run tests
echo ""
echo "🧪 Running tests..."
echo ""

# Default to unit tests if no args provided
if [ $# -eq 0 ]; then
    pytest -m 'not e2e and not integration' "$@"
else
    pytest "$@"
fi

TEST_EXIT_CODE=$?

# Show test result
echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ All tests passed!"
else
    echo "❌ Some tests failed (exit code: $TEST_EXIT_CODE)"
fi

exit $TEST_EXIT_CODE

