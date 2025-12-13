#!/bin/bash
# Generate protobuf files for task_derivation service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "📦 Generating protos for task_derivation service..."

# Create gen directory
mkdir -p services/task_derivation/gen

# Generate task_derivation proto
echo "  Generating task_derivation..."
python -m grpc_tools.protoc \
    --proto_path=specs/fleet/task_derivation/v1 \
    --python_out=services/task_derivation/gen \
    --pyi_out=services/task_derivation/gen \
    --grpc_python_out=services/task_derivation/gen \
    specs/fleet/task_derivation/v1/task_derivation.proto

# Fix imports in task_derivation grpc file
python << 'EOF'
import re
with open('services/task_derivation/gen/task_derivation_pb2_grpc.py', 'r') as f:
    content = f.read()
content = re.sub(r'^import task_derivation_pb2', r'from . import task_derivation_pb2', content, flags=re.MULTILINE)
with open('services/task_derivation/gen/task_derivation_pb2_grpc.py', 'w') as f:
    f.write(content)
EOF

# Generate context proto (needed for Context Service adapter)
echo "  Generating context..."
python -m grpc_tools.protoc \
    --proto_path=specs/fleet/context/v1 \
    --python_out=services/task_derivation/gen \
    --pyi_out=services/task_derivation/gen \
    --grpc_python_out=services/task_derivation/gen \
    specs/fleet/context/v1/context.proto

python << 'EOF'
import re
with open('services/task_derivation/gen/context_pb2_grpc.py', 'r') as f:
    content = f.read()
content = re.sub(r'^import context_pb2', r'from . import context_pb2', content, flags=re.MULTILINE)
with open('services/task_derivation/gen/context_pb2_grpc.py', 'w') as f:
    f.write(content)
EOF

# Generate ray_executor proto (needed for Ray Executor adapter)
echo "  Generating ray_executor..."
python -m grpc_tools.protoc \
    --proto_path=specs/fleet/ray_executor/v1 \
    --python_out=services/task_derivation/gen \
    --pyi_out=services/task_derivation/gen \
    --grpc_python_out=services/task_derivation/gen \
    specs/fleet/ray_executor/v1/ray_executor.proto

python << 'EOF'
import re
with open('services/task_derivation/gen/ray_executor_pb2_grpc.py', 'r') as f:
    content = f.read()
content = re.sub(r'^import ray_executor_pb2', r'from . import ray_executor_pb2', content, flags=re.MULTILINE)
with open('services/task_derivation/gen/ray_executor_pb2_grpc.py', 'w') as f:
    f.write(content)
EOF

# Fix imports in ray_executor_pb2.py
if [ -f "services/task_derivation/gen/ray_executor_pb2.py" ]; then
    python << 'EOF'
import re
with open('services/task_derivation/gen/ray_executor_pb2.py', 'r') as f:
    content = f.read()
content = re.sub(
    r'^from fleet\.ray_executor\.v1 import ray_executor_pb2',
    r'from . import ray_executor_pb2',
    content,
    flags=re.MULTILINE
)
with open('services/task_derivation/gen/ray_executor_pb2.py', 'w') as f:
    f.write(content)
EOF
fi

# Create __init__.py
cat > services/task_derivation/gen/__init__.py << 'EOF'
__all__ = ['task_derivation_pb2', 'task_derivation_pb2_grpc', 'context_pb2', 'context_pb2_grpc', 'ray_executor_pb2', 'ray_executor_pb2_grpc']
EOF

echo "✅ Protos generated for task_derivation service"

