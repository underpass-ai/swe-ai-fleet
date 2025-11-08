#!/bin/bash
# Fix coverage.xml paths for SonarCloud compatibility
# Problem: coverage.py generates paths relative to <source> tags (absolute paths)
# Solution: Convert to paths relative to repository root

if [ ! -f coverage.xml ]; then
    echo "❌ coverage.xml not found"
    exit 1
fi

echo "🔧 Fixing coverage.xml paths for SonarCloud..."

# Get the repository root (where this script is run from)
REPO_ROOT="$(pwd)"

# Fix absolute source paths to be relative (repository root)
# Before: <source>/home/tirso/ai/developents/swe-ai-fleet/core</source>
# After:  <source>.</source>
sed -i "s|<source>${REPO_ROOT}/[^<]*</source>|<source>.</source>|g" coverage.xml
sed -i 's|<source>/home/runner/work/swe-ai-fleet/swe-ai-fleet/[^<]*</source>|<source>.</source>|g' coverage.xml

# Fix file paths to include proper prefixes
# Core files: agents_and_tools/... -> core/agents_and_tools/...
sed -i 's|filename="agents_and_tools/|filename="core/agents_and_tools/|g' coverage.xml
sed -i 's|filename="context/|filename="core/context/|g' coverage.xml
sed -i 's|filename="reports/|filename="core/reports/|g' coverage.xml
sed -i 's|filename="shared/|filename="core/shared/|g' coverage.xml

# Service files: workflow/... -> services/workflow/...
sed -i 's|filename="workflow/|filename="services/workflow/|g' coverage.xml
sed -i 's|filename="orchestrator/|filename="services/orchestrator/|g' coverage.xml
sed -i 's|filename="monitoring/|filename="services/monitoring/|g' coverage.xml
sed -i 's|filename="planning/|filename="services/planning/|g' coverage.xml
sed -i 's|filename="ray_executor/|filename="services/ray_executor/|g' coverage.xml

echo "✅ coverage.xml paths fixed"
echo "📄 Verification:"
echo "   Sources: $(grep -c '<source>\.</source>' coverage.xml) (should be 1+)"
echo "   Core files: $(grep -c 'filename="core/' coverage.xml)"
echo "   Service files: $(grep -c 'filename="services/' coverage.xml)"
echo ""
echo "Sample paths:"
grep 'filename="core/context' coverage.xml | head -2
grep 'filename="services/workflow' coverage.xml | head -2

