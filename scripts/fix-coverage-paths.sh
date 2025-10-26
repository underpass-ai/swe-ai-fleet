#!/bin/bash
# Fix coverage.xml paths from runner absolute to workspace relative
# Convert /home/runner/work/swe-ai-fleet/swe-ai-fleet/ -> (empty)
# So paths like /home/runner/work/swe-ai-fleet/swe-ai-fleet/core become core

if [ -f coverage.xml ]; then
    echo "🔧 Fixing coverage.xml paths for SonarCloud..."
    sed -i 's|/home/runner/work/swe-ai-fleet/swe-ai-fleet/||g' coverage.xml
    echo "✅ coverage.xml paths fixed"
else
    echo "❌ coverage.xml not found"
    exit 1
fi
