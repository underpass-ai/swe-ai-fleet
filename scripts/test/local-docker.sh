#!/bin/bash
# Run module tests in a disposable container (podman/docker) with correct Python and constraints.
# Usage: scripts/test/local-docker.sh <module-path> [pytest-args...]
# Examples:
#   scripts/test/local-docker.sh services/planning
#   scripts/test/local-docker.sh services/ray_executor -k "my_test" -vv

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Pick engine: podman if available, else docker
ENGINE="podman"
if ! command -v podman >/dev/null 2>&1; then
  ENGINE="docker"
fi

if [ $# -lt 1 ]; then
    echo "Usage: $0 <module-path> [pytest-args...]"
    exit 1
fi

MODULE_PATH="$1"
shift
PYTEST_ARGS="$@"

if [ ! -f "$PROJECT_ROOT/$MODULE_PATH/pyproject.toml" ]; then
    echo "❌ $MODULE_PATH/pyproject.toml not found"
    exit 1
fi

# Decide Python image and constraints
PY_IMAGE="python:3.13-slim"
CONSTRAINTS="constraints.txt"
PREINSTALL=""
GEN_CMDS=""
PROTO_PKGS="pip install -c $CONSTRAINTS grpcio-tools==1.68.1 protobuf==5.28.3"

if [[ "$MODULE_PATH" == services/ray_executor* || "$MODULE_PATH" == core/ray_jobs* ]]; then
    PY_IMAGE="python:3.11-slim"
    CONSTRAINTS="constraints-py311.txt"
    PREINSTALL='pip install -c constraints-py311.txt -e core/ray_jobs[dev]'
    # Ray executor tests need orchestrator protos for mapper imports
    GEN_CMDS+="if [ -f services/orchestrator/generate-protos.sh ]; then bash services/orchestrator/generate-protos.sh; fi; "
fi

# Generate protos for the target module if script exists
if [ -f "$PROJECT_ROOT/$MODULE_PATH/generate-protos.sh" ]; then
    GEN_CMDS+="if [ -f $MODULE_PATH/generate-protos.sh ]; then bash $MODULE_PATH/generate-protos.sh; fi; "
fi

$ENGINE run --rm -t \
  -v "$PROJECT_ROOT":/app \
  -w /app \
  "$PY_IMAGE" \
  bash -lc "
    set -euo pipefail
    apt-get update && apt-get install -y --no-install-recommends build-essential git && \
    pip install --upgrade pip && \
    $PROTO_PKGS && \
    # Install monorepo modules first so local (core/*) deps resolve.
    bash scripts/install-modules.sh && \
    if [ -n \"$PREINSTALL\" ]; then eval \"$PREINSTALL\"; fi && \
    $GEN_CMDS \
    pip install -c $CONSTRAINTS -e $MODULE_PATH[dev] && \
    bash scripts/test-module.sh $MODULE_PATH $PYTEST_ARGS
  "
