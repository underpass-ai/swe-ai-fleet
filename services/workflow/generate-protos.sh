#!/bin/bash
# Generate protobuf files for workflow service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "📦 Generating protos for workflow service..."

# Create gen directory
mkdir -p services/workflow/gen

# Generate workflow proto
echo "  Generating workflow..."
python -m grpc_tools.protoc \
    --proto_path=specs/fleet/workflow/v1 \
    --python_out=services/workflow/gen \
    --pyi_out=services/workflow/gen \
    --grpc_python_out=services/workflow/gen \
    specs/fleet/workflow/v1/workflow.proto

# Fix imports in workflow grpc file
python << 'EOF'
import re
with open('services/workflow/gen/workflow_pb2_grpc.py', 'r') as f:
    content = f.read()
content = re.sub(r'^import workflow_pb2', r'from . import workflow_pb2', content, flags=re.MULTILINE)
with open('services/workflow/gen/workflow_pb2_grpc.py', 'w') as f:
    f.write(content)
EOF

# Create __init__.py
cat > services/workflow/gen/__init__.py << 'EOF'
__all__ = ['workflow_pb2', 'workflow_pb2_grpc']
EOF

echo "✅ Protos generated for workflow service"

