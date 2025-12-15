#!/bin/bash
# Generate protobuf files for backlog_review_processor service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "📦 Generating protos for backlog_review_processor service..."

# Ensure grpcio-tools is available for generation (pinned by repo constraints).
pip install -c "$PROJECT_ROOT/constraints.txt" grpcio-tools

# Create gen directory
mkdir -p services/backlog_review_processor/gen

# Generate planning proto (client)
echo "  Generating planning (client)..."
python -m grpc_tools.protoc \
    --proto_path=specs/fleet/planning/v2 \
    --python_out=services/backlog_review_processor/gen \
    --pyi_out=services/backlog_review_processor/gen \
    --grpc_python_out=services/backlog_review_processor/gen \
    specs/fleet/planning/v2/planning.proto

# Fix imports in planning grpc file
python << 'EOF'
import re
with open('services/backlog_review_processor/gen/planning_pb2_grpc.py', 'r') as f:
    content = f.read()
content = re.sub(r'^import planning_pb2', r'from backlog_review_processor.gen import planning_pb2', content, flags=re.MULTILINE)
with open('services/backlog_review_processor/gen/planning_pb2_grpc.py', 'w') as f:
    f.write(content)
EOF

# Generate ray_executor proto (client)
echo "  Generating ray_executor (client)..."
python -m grpc_tools.protoc \
    --proto_path=specs/fleet/ray_executor/v1 \
    --python_out=services/backlog_review_processor/gen \
    --pyi_out=services/backlog_review_processor/gen \
    --grpc_python_out=services/backlog_review_processor/gen \
    specs/fleet/ray_executor/v1/ray_executor.proto

# Fix imports in ray_executor grpc file
python << 'EOF'
import re
with open('services/backlog_review_processor/gen/ray_executor_pb2_grpc.py', 'r') as f:
    content = f.read()
content = re.sub(r'^import ray_executor_pb2', r'from backlog_review_processor.gen import ray_executor_pb2', content, flags=re.MULTILINE)
with open('services/backlog_review_processor/gen/ray_executor_pb2_grpc.py', 'w') as f:
    f.write(content)
EOF

# Create __init__.py
cat > services/backlog_review_processor/gen/__init__.py << 'EOF'
__all__ = ['planning_pb2', 'planning_pb2_grpc', 'ray_executor_pb2', 'ray_executor_pb2_grpc']
EOF

echo "✅ Protos generated for backlog_review_processor service"

