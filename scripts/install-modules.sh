#!/usr/bin/env bash
# Install project modules in dependency order.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# shellcheck source=scripts/lib/modules.sh
source "$PROJECT_ROOT/scripts/lib/modules.sh"

cd "$PROJECT_ROOT"

PY_MINOR="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
CONSTRAINTS_FILE="$PROJECT_ROOT/constraints.txt"
if [ "$PY_MINOR" = "3.11" ]; then
    CONSTRAINTS_FILE="$PROJECT_ROOT/constraints-py311.txt"
fi

if [ ! -f "$CONSTRAINTS_FILE" ]; then
    echo "ERROR: constraints file not found: $CONSTRAINTS_FILE" >&2
    exit 1
fi

echo "Installing modules in dependency order"
echo "Python: $PY_MINOR"
echo "Constraints: $CONSTRAINTS_FILE"

echo "Installing core modules..."
for module in "${CORE_MODULES_PY313[@]}"; do
    if [ "$PY_MINOR" = "3.11" ]; then
        echo "- skip $module (requires Python >= 3.13)"
        continue
    fi
    if [ ! -f "$module/pyproject.toml" ]; then
        echo "- skip $module (no pyproject.toml)"
        continue
    fi
    echo "- install $module"
    pip install -c "$CONSTRAINTS_FILE" -e "$module[dev]"
done

for module in "${CORE_MODULES_PY311[@]}"; do
    if [ "$PY_MINOR" != "3.11" ]; then
        echo "- skip $module (requires Python 3.11)"
        continue
    fi
    if [ ! -f "$module/pyproject.toml" ]; then
        echo "- skip $module (no pyproject.toml)"
        continue
    fi
    echo "- install $module"
    pip install -c "$CONSTRAINTS_FILE" -e "$module[dev]"
done

echo "Installing service modules..."
for module in "${SERVICE_MODULES_PY313[@]}"; do
    if [ "$PY_MINOR" = "3.11" ]; then
        echo "- skip $module (requires Python >= 3.13)"
        continue
    fi
    if [ ! -f "$module/pyproject.toml" ]; then
        echo "- skip $module (no pyproject.toml)"
        continue
    fi
    echo "- install $module"
    pip install -c "$CONSTRAINTS_FILE" -e "$module[dev]"
done

for module in "${SERVICE_MODULES_PY311[@]}"; do
    if [ "$PY_MINOR" != "3.11" ]; then
        echo "- skip $module (requires Python 3.11)"
        continue
    fi
    if [ ! -f "$module/pyproject.toml" ]; then
        echo "- skip $module (no pyproject.toml)"
        continue
    fi
    echo "- install $module"
    pip install -c "$CONSTRAINTS_FILE" -e "$module[dev]"
done

echo "Module installation completed."
