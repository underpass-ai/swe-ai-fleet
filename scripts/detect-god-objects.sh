#!/bin/bash
# God Object Detection Script
# Detects architectural violations in microservices
#
# Usage: ./scripts/detect-god-objects.sh
#
# Thresholds:
#   🟢 OK: <500 lines, <10 methods, <5 adapter calls
#   🟡 WARNING: 500-700 lines, 10-15 methods, 5-10 adapter calls
#   🔴 CRITICAL: >700 lines, >15 methods, >10 adapter calls

set -euo pipefail

echo "🔍 God Object Detection Report"
echo "=============================="
echo "Date: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

total_violations=0

for service in planning context orchestrator workflow monitoring ray_executor; do
    if [ -f "services/$service/server.py" ]; then
        lines=$(wc -l < "services/$service/server.py" 2>/dev/null)
        methods=$(grep -c "^[[:space:]]*def " "services/$service/server.py" 2>/dev/null || echo 0)
        classes=$(grep -c "^class " "services/$service/server.py" 2>/dev/null || echo 0)
        adapters=$(grep -c "self\.graph\|self\.redis\|self\.nats\|self\.neo4j\|self\.valkey" "services/$service/server.py" 2>/dev/null || echo 0)

        # Scoring (higher = worse)
        # Simplified: lines/10 + methods*2 + adapters*5
        lines_score=$((lines / 10))
        methods_score=$((methods * 2))
        adapters_score=$((adapters * 5))
        score=$((lines_score + methods_score + adapters_score))

        # Status determination
        status="🟢 OK"
        level="OK"

        if [ $lines -gt 500 ] || [ $methods -gt 10 ] || [ $adapters -gt 5 ]; then
            status="🟡 WARNING"
            level="WARNING"
            total_violations=$((total_violations + 1))
        fi

        if [ $lines -gt 700 ] || [ $methods -gt 15 ] || [ $adapters -gt 10 ]; then
            status="🔴 CRITICAL"
            level="CRITICAL"
        fi

        echo "$status $service Service"
        echo "  Lines: $lines (threshold: 🟢<500 🟡500-700 🔴>700)"
        echo "  Methods: $methods (threshold: 🟢<10 🟡10-15 🔴>15)"
        echo "  Direct adapter calls: $adapters (threshold: 🟢<5 🟡5-10 🔴>10)"
        echo "  God Object Score: $score (higher = worse)"
        echo ""
    fi
done

echo "=============================="
echo "Summary:"
echo "  Total services audited: 6"
echo "  Services with violations: $total_violations"
echo ""

if [ $total_violations -gt 3 ]; then
    echo "❌ SYSTEM STATUS: CRITICAL (>3 violations)"
    echo "   Recommended: Prioritize refactoring"
    exit 1
elif [ $total_violations -gt 1 ]; then
    echo "⚠️  SYSTEM STATUS: WARNING (1-3 violations)"
    echo "   Recommended: Schedule refactoring"
    exit 0
else
    echo "✅ SYSTEM STATUS: HEALTHY"
    exit 0
fi

