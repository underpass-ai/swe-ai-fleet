#!/bin/bash
# Run tests for a module locally with the correct Python/constraints.
# Usage: scripts/test/local.sh <module-path> [pytest-args...]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

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

# Select constraints and expected Python range
CONSTRAINTS="$PROJECT_ROOT/constraints.txt"
REQ_LOWER=3
REQ_UPPER=99
if [[ "$MODULE_PATH" == services/ray_executor* || "$MODULE_PATH" == core/ray_jobs* ]]; then
    CONSTRAINTS="$PROJECT_ROOT/constraints-py311.txt"
    REQ_LOWER=3.11
    REQ_UPPER=3.12
else
    REQ_LOWER=3.13
    REQ_UPPER=4.0
fi

# Validate Python version
python - <<PY
import sys
def parse_version(v: str) -> tuple[int, int]:
    major_s, minor_s = v.split(".", 1)
    return int(major_s), int(minor_s)

lower_s = "$REQ_LOWER"
upper_s = "$REQ_UPPER"
lower = parse_version(lower_s)
upper = parse_version(upper_s)
ver = (sys.version_info.major, sys.version_info.minor)
if not (lower <= ver < upper):
    raise SystemExit(
        f"Python {ver[0]}.{ver[1]} not supported for this module; expected [{lower_s}, {upper_s})"
    )
PY

cd "$PROJECT_ROOT"

# For ray_executor ensure core/ray_jobs is installed first
if [[ "$MODULE_PATH" == services/ray_executor* ]]; then
    if [ -f "core/ray_jobs/pyproject.toml" ]; then
        echo "📦 Installing core/ray_jobs with constraints ($CONSTRAINTS)..."
        pip install -c "$CONSTRAINTS" -e "core/ray_jobs[dev]"
    fi
fi

echo "📦 Installing $MODULE_PATH with constraints ($CONSTRAINTS)..."
pip install -c "$CONSTRAINTS" -e "$MODULE_PATH[dev]"

echo "🧪 Running tests for $MODULE_PATH ..."
bash "$PROJECT_ROOT/scripts/test/test-module.sh" "$MODULE_PATH" $PYTEST_ARGS
