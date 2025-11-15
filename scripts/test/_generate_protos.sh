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

    # Helper function to fix imports (portable across bash/zsh/macOS)
    _fix_imports() {
        local file="$1"
        local pb2_module="$2"
        if [ -f "$file" ]; then
            python << EOF
import re
with open('$file', 'r') as f:
    content = f.read()
content = re.sub(r'^import ${pb2_module}_pb2', r'from . import ${pb2_module}_pb2', content, flags=re.MULTILINE)
with open('$file', 'w') as f:
    f.write(content)
EOF
        fi
    }

    # Fix imports in orchestrator grpc files
    _fix_imports services/orchestrator/gen/orchestrator_pb2_grpc.py orchestrator
    _fix_imports services/orchestrator/gen/ray_executor_pb2_grpc.py ray_executor

    # Generate context stubs
    echo "📦 Generating context stubs..."
    python -m grpc_tools.protoc \
        --python_out=services/context/gen \
        --grpc_python_out=services/context/gen \
        --proto_path=specs/fleet/context/v1 \
        specs/fleet/context/v1/context.proto

    # Fix imports in context grpc files
    _fix_imports services/context/gen/context_pb2_grpc.py context

    # Generate planning service stubs
    echo "📦 Generating planning stubs..."
    python -m grpc_tools.protoc \
        --python_out=services/planning/planning/gen \
        --pyi_out=services/planning/planning/gen \
        --grpc_python_out=services/planning/planning/gen \
        --proto_path=specs/fleet/planning/v2 \
        specs/fleet/planning/v2/planning.proto

    # Fix imports in planning grpc files
    _fix_imports services/planning/planning/gen/planning_pb2_grpc.py planning

    # Generate task derivation stubs
    echo "📦 Generating task-derivation stubs..."
    python -m grpc_tools.protoc \
        --python_out=services/task-derivation/task_derivation/gen \
        --pyi_out=services/task-derivation/task_derivation/gen \
        --grpc_python_out=services/task-derivation/task_derivation/gen \
        --proto_path=specs/fleet/task_derivation/v1 \
        specs/fleet/task_derivation/v1/task_derivation.proto

    _fix_imports services/task-derivation/task_derivation/gen/task_derivation_pb2_grpc.py task_derivation

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
