#!/bin/bash
# Generate protobuf files for ray_executor service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "📦 Generating protos for ray_executor service..."

# Create gen directory
mkdir -p services/ray_executor/gen

# Generate ray_executor proto
echo "  Generating ray_executor..."
python -m grpc_tools.protoc \
    --proto_path=specs/fleet/ray_executor/v1 \
    --python_out=services/ray_executor/gen \
    --pyi_out=services/ray_executor/gen \
    --grpc_python_out=services/ray_executor/gen \
    specs/fleet/ray_executor/v1/ray_executor.proto

# Fix imports in ray_executor grpc file
python << 'EOF'
import re
with open('services/ray_executor/gen/ray_executor_pb2_grpc.py', 'r') as f:
    content = f.read()
content = re.sub(r'^import ray_executor_pb2', r'from . import ray_executor_pb2', content, flags=re.MULTILINE)
with open('services/ray_executor/gen/ray_executor_pb2_grpc.py', 'w') as f:
    f.write(content)
EOF

# Create __init__.py
cat > services/ray_executor/gen/__init__.py << 'EOF'
__all__ = ['ray_executor_pb2', 'ray_executor_pb2_grpc']
EOF

echo "✅ Protos generated for ray_executor service"

