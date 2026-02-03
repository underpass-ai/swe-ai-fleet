#!/bin/bash
# Generate protobuf stubs for planning_ceremony_processor (planning_ceremony + ray_executor).
# Run from project root.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "📦 Generating protos for planning_ceremony_processor..."

pip install -q -c "$PROJECT_ROOT/constraints.txt" grpcio-tools

mkdir -p services/planning_ceremony_processor/gen

echo "  Generating planning_ceremony..."
python -m grpc_tools.protoc \
    --proto_path=specs/fleet/planning_ceremony/v1 \
    --python_out=services/planning_ceremony_processor/gen \
    --pyi_out=services/planning_ceremony_processor/gen \
    --grpc_python_out=services/planning_ceremony_processor/gen \
    specs/fleet/planning_ceremony/v1/planning_ceremony.proto

python << 'EOF'
import re
path = 'services/planning_ceremony_processor/gen/planning_ceremony_pb2_grpc.py'
with open(path, 'r') as f:
    c = f.read()
c = re.sub(r'^import planning_ceremony_pb2', 'from . import planning_ceremony_pb2', c, flags=re.M)
with open(path, 'w') as f:
    f.write(c)
EOF

echo "  Generating ray_executor..."
python -m grpc_tools.protoc \
    --proto_path=specs/fleet/ray_executor/v1 \
    --python_out=services/planning_ceremony_processor/gen \
    --pyi_out=services/planning_ceremony_processor/gen \
    --grpc_python_out=services/planning_ceremony_processor/gen \
    specs/fleet/ray_executor/v1/ray_executor.proto

python << 'EOF'
import re
path = 'services/planning_ceremony_processor/gen/ray_executor_pb2_grpc.py'
with open(path, 'r') as f:
    c = f.read()
c = re.sub(r'^import ray_executor_pb2', 'from . import ray_executor_pb2', c, flags=re.M)
with open(path, 'w') as f:
    f.write(c)
EOF

touch services/planning_ceremony_processor/gen/__init__.py
echo "✅ Protos generated in services/planning_ceremony_processor/gen/"
