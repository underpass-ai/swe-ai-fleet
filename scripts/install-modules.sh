#!/bin/bash
# Install all modules in dependency order
# Core modules first, then services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "📦 Installing modules in dependency order..."
echo ""

# Select constraints based on the running interpreter.
PY_MINOR="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
CONSTRAINTS_FILE="$PROJECT_ROOT/constraints.txt"
if [ "$PY_MINOR" = "3.11" ]; then
    CONSTRAINTS_FILE="$PROJECT_ROOT/constraints-py311.txt"
fi

if [ ! -f "$CONSTRAINTS_FILE" ]; then
    echo "❌ Constraints file not found: $CONSTRAINTS_FILE"
    echo "Expected one of:"
    echo "  - $PROJECT_ROOT/constraints.txt (Python 3.13 baseline)"
    echo "  - $PROJECT_ROOT/constraints-py311.txt (Python 3.11 baseline)"
    exit 1
fi

echo "🐍 Python: $PY_MINOR"
echo "📌 Constraints: $CONSTRAINTS_FILE"
echo ""

# Install core modules first (no dependencies on other core modules)
CORE_MODULES=(
    "core/shared"
    "core/memory"
    "core/context"
    "core/ceremony_engine"
    "core/orchestrator"
    "core/agents_and_tools"
    "core/ray_jobs"
    "core/reports"
)

echo "🔧 Installing core modules..."
for module in "${CORE_MODULES[@]}"; do
    # Ray modules are Python 3.11-only.
    if [ "$PY_MINOR" != "3.11" ] && [ "$module" = "core/ray_jobs" ]; then
        echo "  ⏭️  Skipping $module (requires Python 3.11)"
        continue
    fi
    if [ "$PY_MINOR" = "3.11" ] && [ "$module" != "core/ray_jobs" ]; then
        echo "  ⏭️  Skipping $module (requires Python >= 3.13)"
        continue
    fi

    if [ -f "$module/pyproject.toml" ]; then
        echo "  Installing $module..."
        # Install with dev dependencies (includes pytest, pytest-asyncio, pytest-cov, etc.)
        pip install -c "$CONSTRAINTS_FILE" -e "$module[dev]" || {
            echo "❌ Failed to install $module"
            exit 1
        }
    else
        echo "  ⚠️  Skipping $module (no pyproject.toml)"
    fi
done

echo ""
echo "🔧 Installing service modules..."
# Install service modules (may depend on core modules)
SERVICE_MODULES=(
    "services/backlog_review_processor"
    "services/context"
    "services/orchestrator"
    "services/planning"
    "services/ray_executor"
    "services/task_derivation"
    "services/workflow"
)

for module in "${SERVICE_MODULES[@]}"; do
    # Ray executor is Python 3.11-only.
    if [ "$PY_MINOR" != "3.11" ] && [ "$module" = "services/ray_executor" ]; then
        echo "  ⏭️  Skipping $module (requires Python 3.11)"
        continue
    fi
    if [ "$PY_MINOR" = "3.11" ] && [ "$module" != "services/ray_executor" ]; then
        echo "  ⏭️  Skipping $module (requires Python >= 3.13)"
        continue
    fi

    if [ -f "$module/pyproject.toml" ]; then
        echo "  Installing $module..."
        # Install with dev dependencies (includes pytest, pytest-asyncio, pytest-cov, etc.)
        pip install -c "$CONSTRAINTS_FILE" -e "$module[dev]" || {
            echo "❌ Failed to install $module"
            exit 1
        }
    else
        echo "  ⚠️  Skipping $module (no pyproject.toml)"
    fi
done

echo ""
echo "✅ All modules installed successfully"
