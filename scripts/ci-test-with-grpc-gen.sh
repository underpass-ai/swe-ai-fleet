#!/bin/bash
# Generate gRPC stubs for tests and clean up afterwards

set -e

# Activate virtual environment if exists
if [ -f .venv/bin/activate ]; then
    echo "🐍 Activating virtual environment..."
    source .venv/bin/activate
fi

echo "🔧 Generating gRPC stubs for tests..."

# Create gen directories
mkdir -p services/orchestrator/gen
mkdir -p services/context/gen
mkdir -p services/monitoring/gen

# Generate orchestrator stubs
echo "📦 Generating orchestrator stubs..."
python -m grpc_tools.protoc \
    --python_out=services/orchestrator/gen \
    --grpc_python_out=services/orchestrator/gen \
    --proto_path=specs \
    specs/orchestrator.proto specs/ray_executor.proto

# Fix imports in orchestrator grpc files
sed -i 's/^import orchestrator_pb2/from . import orchestrator_pb2/' services/orchestrator/gen/orchestrator_pb2_grpc.py
sed -i 's/^import ray_executor_pb2/from . import ray_executor_pb2/' services/orchestrator/gen/ray_executor_pb2_grpc.py

# Generate context stubs
echo "📦 Generating context stubs..."
python -m grpc_tools.protoc \
    --python_out=services/context/gen \
    --grpc_python_out=services/context/gen \
    --proto_path=specs \
    specs/context.proto

# Fix imports in context grpc files
sed -i 's/^import context_pb2/from . import context_pb2/' services/context/gen/context_pb2_grpc.py

# Generate monitoring stubs
echo "📦 Generating monitoring stubs..."
python -m grpc_tools.protoc \
    --python_out=services/monitoring/gen \
    --grpc_python_out=services/monitoring/gen \
    --proto_path=specs \
    specs/orchestrator.proto specs/ray_executor.proto

# Fix imports in monitoring grpc files
sed -i 's/^import orchestrator_pb2/from . import orchestrator_pb2/' services/monitoring/gen/orchestrator_pb2_grpc.py
sed -i 's/^import ray_executor_pb2/from . import ray_executor_pb2/' services/monitoring/gen/ray_executor_pb2_grpc.py

# Create __init__.py files
echo "📝 Creating __init__.py files..."
echo "__all__ = ['orchestrator_pb2', 'orchestrator_pb2_grpc', 'ray_executor_pb2', 'ray_executor_pb2_grpc']" > services/orchestrator/gen/__init__.py
echo "__all__ = ['context_pb2', 'context_pb2_grpc']" > services/context/gen/__init__.py
echo "__all__ = ['orchestrator_pb2', 'orchestrator_pb2_grpc', 'ray_executor_pb2', 'ray_executor_pb2_grpc']" > services/monitoring/gen/__init__.py

echo "✅ gRPC stubs generated successfully"

# Function to clean up stubs
cleanup_stubs() {
    echo "🧹 Cleaning up generated stubs..."
    rm -rf services/orchestrator/gen
    rm -rf services/context/gen
    rm -rf services/monitoring/gen
    echo "✅ Cleanup completed"
}

# Set up trap to clean up on exit
trap cleanup_stubs EXIT

# Run tests
echo "🧪 Running tests..."
pytest -m 'not e2e and not integration' -v --tb=short "$@"

echo "✅ Tests completed"

