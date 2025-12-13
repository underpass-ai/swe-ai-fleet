#!/bin/bash
# Run all tests (unit tests only)
# Usage: ./scripts/test/all.sh
# Note: Integration and E2E tests have been removed and will be reimplemented from scratch

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "╔═══════════════════════════════════════════╗"
echo "║       Running ALL Tests Suite             ║"
echo "╚═══════════════════════════════════════════╝"
echo ""

# Run unit tests
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 UNIT TESTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
bash "$SCRIPT_DIR/unit.sh" || {
    echo "❌ Unit tests failed, aborting"
    exit 1
}

echo ""
echo "╔═══════════════════════════════════════════╗"
echo "║   ✅ ALL TESTS PASSED SUCCESSFULLY! ✅    ║"
echo "╚═══════════════════════════════════════════╝"
echo ""
echo "ℹ️  Note: Integration and E2E tests have been removed."
echo "   They will be reimplemented from scratch in the future."

