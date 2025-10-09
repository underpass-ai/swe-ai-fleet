#!/bin/bash
# Script to build Docker images and run integration tests

set -e

echo "🔨 Building Orchestrator Docker image..."
docker build -t localhost:5000/swe-ai-fleet/orchestrator:latest \
  -f services/orchestrator/Dockerfile .

echo "✅ Docker image built successfully"

echo ""
echo "🧪 Running integration tests..."
pytest tests/integration/services/orchestrator/ \
  -v \
  -m integration \
  --tb=short

echo ""
echo "✅ Integration tests completed!"

