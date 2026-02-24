#!/bin/bash
# Generate protobuf files for a specific module
# Usage: ./scripts/dev/generate-protos-module.sh <module-path> [proto-files...]
#
# If proto-files are not provided, the script will look for a generate-protos.sh
# in the module directory

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <module-path> [proto-files...]"
    echo "Example: $0 services/orchestrator"
    exit 1
fi

MODULE_PATH="$1"
shift
PROTO_FILES="$@"

cd "$PROJECT_ROOT"

if [ ! -d "$MODULE_PATH" ]; then
    echo "❌ Error: Module directory not found: $MODULE_PATH"
    exit 1
fi

# Check if module has its own generate-protos script
if [ -f "$MODULE_PATH/generate-protos.sh" ]; then
    echo "📦 Generating protos for $MODULE_PATH using module script..."
    cd "$MODULE_PATH"
    bash generate-protos.sh
    exit 0
fi

# If proto files are specified, generate them
if [ -n "$PROTO_FILES" ]; then
    echo "📦 Generating protos for $MODULE_PATH..."

    # Create gen directory
    mkdir -p "$MODULE_PATH/gen"

    # Generate each proto file
    for proto_file in $PROTO_FILES; do
        if [ ! -f "$proto_file" ]; then
            echo "⚠️  Warning: Proto file not found: $proto_file"
            continue
        fi

        proto_name=$(basename "$proto_file" .proto)
        proto_dir=$(dirname "$proto_file")

        echo "  Generating $proto_name..."
        python -m grpc_tools.protoc \
            --proto_path="$proto_dir" \
            --python_out="$MODULE_PATH/gen" \
            --pyi_out="$MODULE_PATH/gen" \
            --grpc_python_out="$MODULE_PATH/gen" \
            "$proto_file"

        # Fix imports in grpc file
        grpc_file="$MODULE_PATH/gen/${proto_name}_pb2_grpc.py"
        if [ -f "$grpc_file" ]; then
            python << EOF
import re
with open('$grpc_file', 'r') as f:
    content = f.read()
content = re.sub(r'^import ${proto_name}_pb2', r'from . import ${proto_name}_pb2', content, flags=re.MULTILINE)
with open('$grpc_file', 'w') as f:
    f.write(content)
EOF
        fi
    done

    # Create __init__.py
    echo "# Generated protobuf files" > "$MODULE_PATH/gen/__init__.py"
    echo "__all__ = [" >> "$MODULE_PATH/gen/__init__.py"
    for proto_file in $PROTO_FILES; do
        proto_name=$(basename "$proto_file" .proto)
        echo "    '${proto_name}_pb2'," >> "$MODULE_PATH/gen/__init__.py"
        echo "    '${proto_name}_pb2_grpc'," >> "$MODULE_PATH/gen/__init__.py"
    done
    echo "]" >> "$MODULE_PATH/gen/__init__.py"

    echo "✅ Protos generated for $MODULE_PATH"
else
    echo "❌ Error: No proto files specified and no generate-protos.sh found in $MODULE_PATH"
    echo "Create $MODULE_PATH/generate-protos.sh or specify proto files"
    exit 1
fi

