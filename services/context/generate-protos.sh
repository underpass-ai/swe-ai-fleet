#!/bin/bash
# Generate protobuf files for context service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "📦 Generating protos for context service..."

# Create gen directory
mkdir -p services/context/gen

# Generate context proto
echo "  Generating context..."
python -m grpc_tools.protoc \
    --proto_path=specs/fleet/context/v1 \
    --python_out=services/context/gen \
    --pyi_out=services/context/gen \
    --grpc_python_out=services/context/gen \
    specs/fleet/context/v1/context.proto

# Fix imports in context grpc file
python << 'EOF'
import re
with open('services/context/gen/context_pb2_grpc.py', 'r') as f:
    content = f.read()
content = re.sub(r'^import context_pb2', r'from . import context_pb2', content, flags=re.MULTILINE)
with open('services/context/gen/context_pb2_grpc.py', 'w') as f:
    f.write(content)
EOF

# Create __init__.py
cat > services/context/gen/__init__.py << 'EOF'
__all__ = ['context_pb2', 'context_pb2_grpc']
EOF

echo "✅ Protos generated for context service"

