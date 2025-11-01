#!/bin/bash
set -e
echo "=== grpcui Interactive gRPC Testing Server ==="
echo ""
TARGET="${GRPCUI_TARGET:-localhost:50055}"
PORT="${GRPCUI_PORT:-8080}"
SERVICE="${GRPCUI_SERVICE:-orchestrator}"
echo "Target gRPC server: $TARGET"
echo "grpcui web UI port: $PORT"
echo "Service: $SERVICE"
echo ""
echo "Starting grpcui with proto files..."
echo "Access the UI at: http://localhost:$PORT"
echo ""

# Use proto files if available, otherwise try reflection
if [ -f "specs/fleet/${SERVICE}/v1/${SERVICE}.proto" ]; then
    echo "Using proto file: specs/fleet/${SERVICE}/v1/${SERVICE}.proto"
    exec grpcui -plaintext -bind 0.0.0.0 -port $PORT -import-path specs/fleet -proto ${SERVICE}/v1/${SERVICE}.proto $TARGET
else
    echo "No proto file found, attempting reflection..."
    exec grpcui -plaintext -bind 0.0.0.0 -port $PORT $TARGET
fi

