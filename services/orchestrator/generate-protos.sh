#!/bin/bash
# Generate protobuf files for orchestrator service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "📦 Generating protos for orchestrator service..."

# Create gen directory
mkdir -p services/orchestrator/gen

# Generate orchestrator proto
echo "  Generating orchestrator..."
python -m grpc_tools.protoc \
    --proto_path=specs/fleet/orchestrator/v1 \
    --python_out=services/orchestrator/gen \
    --pyi_out=services/orchestrator/gen \
    --grpc_python_out=services/orchestrator/gen \
    specs/fleet/orchestrator/v1/orchestrator.proto

# Fix imports in orchestrator grpc file
python << 'EOF'
import re
with open('services/orchestrator/gen/orchestrator_pb2_grpc.py', 'r') as f:
    content = f.read()
content = re.sub(r'^import orchestrator_pb2', r'from . import orchestrator_pb2', content, flags=re.MULTILINE)
with open('services/orchestrator/gen/orchestrator_pb2_grpc.py', 'w') as f:
    f.write(content)
EOF

# Generate ray_executor proto (needed for Ray Executor adapter)
echo "  Generating ray_executor..."
python -m grpc_tools.protoc \
    --proto_path=specs/fleet/ray_executor/v1 \
    --python_out=services/orchestrator/gen \
    --pyi_out=services/orchestrator/gen \
    --grpc_python_out=services/orchestrator/gen \
    specs/fleet/ray_executor/v1/ray_executor.proto

# Fix imports in ray_executor grpc file
python << 'EOF'
import re
with open('services/orchestrator/gen/ray_executor_pb2_grpc.py', 'r') as f:
    content = f.read()
content = re.sub(r'^import ray_executor_pb2', r'from . import ray_executor_pb2', content, flags=re.MULTILINE)
with open('services/orchestrator/gen/ray_executor_pb2_grpc.py', 'w') as f:
    f.write(content)
EOF

# Fix imports in ray_executor_pb2.py
if [ -f "services/orchestrator/gen/ray_executor_pb2.py" ]; then
    python << 'EOF'
import re
with open('services/orchestrator/gen/ray_executor_pb2.py', 'r') as f:
    content = f.read()
content = re.sub(
    r'^from fleet\.ray_executor\.v1 import ray_executor_pb2',
    r'from . import ray_executor_pb2',
    content,
    flags=re.MULTILINE
)
with open('services/orchestrator/gen/ray_executor_pb2.py', 'w') as f:
    f.write(content)
EOF
fi

# Create __init__.py
cat > services/orchestrator/gen/__init__.py << 'EOF'
__all__ = ['orchestrator_pb2', 'orchestrator_pb2_grpc', 'ray_executor_pb2', 'ray_executor_pb2_grpc']
EOF

echo "✅ Protos generated for orchestrator service"

