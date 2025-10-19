#!/bin/bash
# Run all tests (unit, integration, e2e)
# Usage: ./scripts/test/all.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "╔═══════════════════════════════════════════╗"
echo "║       Running ALL Tests Suite             ║"
echo "╚═══════════════════════════════════════════╝"
echo ""

# Run unit tests
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  UNIT TESTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
bash "$SCRIPT_DIR/unit.sh" || {
    echo "❌ Unit tests failed, aborting"
    exit 1
}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  INTEGRATION TESTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
bash "$SCRIPT_DIR/integration.sh" || {
    echo "❌ Integration tests failed, aborting"
    exit 1
}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  E2E TESTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
bash "$SCRIPT_DIR/e2e.sh" || {
    echo "❌ E2E tests failed"
    exit 1
}

echo ""
echo "╔═══════════════════════════════════════════╗"
echo "║   ✅ ALL TESTS PASSED SUCCESSFULLY! ✅    ║"
echo "╚═══════════════════════════════════════════╝"

