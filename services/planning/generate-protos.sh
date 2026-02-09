#!/bin/bash
# Generate protobuf files for planning service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "📦 Generating protos for planning service..."

# Ensure grpcio-tools is available for generation (pinned by repo constraints).
pip install -c "$PROJECT_ROOT/constraints.txt" grpcio-tools

# Create gen directory
mkdir -p services/planning/gen

# Generate planning proto
echo "  Generating planning..."
python -m grpc_tools.protoc \
    --proto_path=specs/fleet/planning/v2 \
    --python_out=services/planning/gen \
    --pyi_out=services/planning/gen \
    --grpc_python_out=services/planning/gen \
    specs/fleet/planning/v2/planning.proto

# Fix imports in planning grpc file
python << 'EOF'
import re
with open('services/planning/gen/planning_pb2_grpc.py', 'r') as f:
    content = f.read()
content = re.sub(r'^import planning_pb2', r'from . import planning_pb2', content, flags=re.MULTILINE)
with open('services/planning/gen/planning_pb2_grpc.py', 'w') as f:
    f.write(content)
EOF

# Generate task_derivation proto (Planning implements this server contract)
echo "  Generating task_derivation..."
python -m grpc_tools.protoc \
    --proto_path=specs/fleet/task_derivation/v1 \
    --python_out=services/planning/gen \
    --pyi_out=services/planning/gen \
    --grpc_python_out=services/planning/gen \
    specs/fleet/task_derivation/v1/task_derivation.proto

python << 'EOF'
import re
with open('services/planning/gen/task_derivation_pb2_grpc.py', 'r') as f:
    content = f.read()
content = re.sub(r'^import task_derivation_pb2', r'from . import task_derivation_pb2', content, flags=re.MULTILINE)
with open('services/planning/gen/task_derivation_pb2_grpc.py', 'w') as f:
    f.write(content)
EOF

# Generate context proto (needed for Context Service adapter)
echo "  Generating context..."
python -m grpc_tools.protoc \
    --proto_path=specs/fleet/context/v1 \
    --python_out=services/planning/gen \
    --pyi_out=services/planning/gen \
    --grpc_python_out=services/planning/gen \
    specs/fleet/context/v1/context.proto

python << 'EOF'
import re
with open('services/planning/gen/context_pb2_grpc.py', 'r') as f:
    content = f.read()
content = re.sub(r'^import context_pb2', r'from . import context_pb2', content, flags=re.MULTILINE)
with open('services/planning/gen/context_pb2_grpc.py', 'w') as f:
    f.write(content)
EOF

# Generate orchestrator proto (needed for Orchestrator Service adapter)
echo "  Generating orchestrator..."
python -m grpc_tools.protoc \
    --proto_path=specs/fleet/orchestrator/v1 \
    --python_out=services/planning/gen \
    --pyi_out=services/planning/gen \
    --grpc_python_out=services/planning/gen \
    specs/fleet/orchestrator/v1/orchestrator.proto

python << 'EOF'
import re
with open('services/planning/gen/orchestrator_pb2_grpc.py', 'r') as f:
    content = f.read()
content = re.sub(r'^import orchestrator_pb2', r'from . import orchestrator_pb2', content, flags=re.MULTILINE)
with open('services/planning/gen/orchestrator_pb2_grpc.py', 'w') as f:
    f.write(content)
EOF

# Generate ray_executor proto (needed for Ray Executor adapter)
echo "  Generating ray_executor..."
python -m grpc_tools.protoc \
    --proto_path=specs/fleet/ray_executor/v1 \
    --python_out=services/planning/gen \
    --pyi_out=services/planning/gen \
    --grpc_python_out=services/planning/gen \
    specs/fleet/ray_executor/v1/ray_executor.proto

python << 'EOF'
import re
with open('services/planning/gen/ray_executor_pb2_grpc.py', 'r') as f:
    content = f.read()
content = re.sub(r'^import ray_executor_pb2', r'from . import ray_executor_pb2', content, flags=re.MULTILINE)
with open('services/planning/gen/ray_executor_pb2_grpc.py', 'w') as f:
    f.write(content)
EOF

# Fix imports in ray_executor_pb2.py
if [ -f "services/planning/gen/ray_executor_pb2.py" ]; then
    python << 'EOF'
import re
with open('services/planning/gen/ray_executor_pb2.py', 'r') as f:
    content = f.read()
content = re.sub(
    r'^from fleet\.ray_executor\.v1 import ray_executor_pb2',
    r'from . import ray_executor_pb2',
    content,
    flags=re.MULTILINE
)
with open('services/planning/gen/ray_executor_pb2.py', 'w') as f:
    f.write(content)
EOF
fi

# Generate planning_ceremony proto (needed for Planning Ceremony Processor thin client)
echo "  Generating planning_ceremony..."
python -m grpc_tools.protoc \
    --proto_path=specs/fleet/planning_ceremony/v1 \
    --python_out=services/planning/gen \
    --pyi_out=services/planning/gen \
    --grpc_python_out=services/planning/gen \
    specs/fleet/planning_ceremony/v1/planning_ceremony.proto

python << 'EOF'
import re
with open('services/planning/gen/planning_ceremony_pb2_grpc.py', 'r') as f:
    content = f.read()
content = re.sub(r'^import planning_ceremony_pb2', 'from . import planning_ceremony_pb2', content, flags=re.MULTILINE)
with open('services/planning/gen/planning_ceremony_pb2_grpc.py', 'w') as f:
    f.write(content)
EOF

# Create __init__.py
cat > services/planning/gen/__init__.py << 'EOF'
__all__ = ['planning_pb2', 'planning_pb2_grpc', 'task_derivation_pb2', 'task_derivation_pb2_grpc', 'context_pb2', 'context_pb2_grpc', 'orchestrator_pb2', 'orchestrator_pb2_grpc', 'ray_executor_pb2', 'ray_executor_pb2_grpc', 'planning_ceremony_pb2', 'planning_ceremony_pb2_grpc']
EOF

echo "✅ Protos generated for planning service"
