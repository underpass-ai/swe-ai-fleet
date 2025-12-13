#!/bin/bash
# Install all modules in dependency order
# Core modules first, then services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "📦 Installing modules in dependency order..."
echo ""

# Install core modules first (no dependencies on other core modules)
CORE_MODULES=(
    "core/shared"
    "core/memory"
    "core/context"
    "core/orchestrator"
    "core/agents_and_tools"
    "core/ray_jobs"
    "core/reports"
)

echo "🔧 Installing core modules..."
for module in "${CORE_MODULES[@]}"; do
    if [ -f "$module/pyproject.toml" ]; then
        echo "  Installing $module..."
        # Install with dev dependencies (includes pytest, pytest-asyncio, pytest-cov, etc.)
        pip install -e "$module[dev]" || {
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
    if [ -f "$module/pyproject.toml" ]; then
        echo "  Installing $module..."
        # Install with dev dependencies (includes pytest, pytest-asyncio, pytest-cov, etc.)
        pip install -e "$module[dev]" || {
            echo "❌ Failed to install $module"
            exit 1
        }
    else
        echo "  ⚠️  Skipping $module (no pyproject.toml)"
    fi
done

echo ""
echo "✅ All modules installed successfully"
