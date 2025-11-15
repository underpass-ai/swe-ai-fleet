#!/bin/bash
# Shared function to generate protobuf files
# Source this file in other test scripts: source scripts/test/_generate_protos.sh

generate_protobuf_files() {
    echo "📦 Generating gRPC stubs for tests..."

    # Create gen directories
    mkdir -p services/orchestrator/gen
    mkdir -p services/context/gen
    mkdir -p services/planning/planning/gen
    mkdir -p services/task-derivation/task_derivation/gen

    # Generate orchestrator stubs
    echo "📦 Generating orchestrator stubs..."
    python -m grpc_tools.protoc \
        --python_out=services/orchestrator/gen \
        --grpc_python_out=services/orchestrator/gen \
        --proto_path=specs/fleet/orchestrator/v1 \
        specs/fleet/orchestrator/v1/orchestrator.proto

    # Fix imports in orchestrator grpc files
    sed -i 's/^import orchestrator_pb2/from . import orchestrator_pb2/' services/orchestrator/gen/orchestrator_pb2_grpc.py 2>/dev/null || true
    sed -i 's/^import ray_executor_pb2/from . import ray_executor_pb2/' services/orchestrator/gen/ray_executor_pb2_grpc.py 2>/dev/null || true

    # Generate context stubs
    echo "📦 Generating context stubs..."
    python -m grpc_tools.protoc \
        --python_out=services/context/gen \
        --grpc_python_out=services/context/gen \
        --proto_path=specs/fleet/context/v1 \
        specs/fleet/context/v1/context.proto

    # Fix imports in context grpc files
    sed -i 's/^import context_pb2/from . import context_pb2/' services/context/gen/context_pb2_grpc.py 2>/dev/null || true

    # Generate planning service stubs
    echo "📦 Generating planning stubs..."
    python -m grpc_tools.protoc \
        --python_out=services/planning/planning/gen \
        --pyi_out=services/planning/planning/gen \
        --grpc_python_out=services/planning/planning/gen \
        --proto_path=specs/fleet/planning/v2 \
        specs/fleet/planning/v2/planning.proto

    # Fix imports in planning grpc files
    sed -i 's/^import planning_pb2/from . import planning_pb2/' services/planning/planning/gen/planning_pb2_grpc.py 2>/dev/null || true

    # Generate task derivation stubs
    echo "📦 Generating task-derivation stubs..."
    python -m grpc_tools.protoc \
        --python_out=services/task-derivation/task_derivation/gen \
        --pyi_out=services/task-derivation/task_derivation/gen \
        --grpc_python_out=services/task-derivation/task_derivation/gen \
        --proto_path=specs/fleet/task_derivation/v1 \
        specs/fleet/task_derivation/v1/task_derivation.proto

    sed -i 's/^import task_derivation_pb2/from . import task_derivation_pb2/' services/task-derivation/task_derivation/gen/task_derivation_pb2_grpc.py 2>/dev/null || true

    # Create __init__.py files
    echo "📝 Creating __init__.py files..."
    echo "__all__ = ['orchestrator_pb2', 'orchestrator_pb2_grpc']" > services/orchestrator/gen/__init__.py
    echo "__all__ = ['context_pb2', 'context_pb2_grpc']" > services/context/gen/__init__.py
    echo "__all__ = ['planning_pb2', 'planning_pb2_grpc']" > services/planning/planning/gen/__init__.py
    echo "__all__ = ['task_derivation_pb2', 'task_derivation_pb2_grpc']" > services/task-derivation/task_derivation/gen/__init__.py

    echo "✅ gRPC stubs generated successfully"
}

cleanup_protobuf_files() {
    echo ""
    echo "🧹 Cleaning up generated stubs..."
    rm -rf services/orchestrator/gen
    rm -rf services/context/gen
    rm -rf services/planning/planning/gen
    rm -rf services/task-derivation/task_derivation/gen
    echo "✅ Cleanup completed"
}

# Export functions
export -f generate_protobuf_files
export -f cleanup_protobuf_files

