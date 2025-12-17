#!/bin/bash
# Check SonarCloud coverage for specific files
# Usage: ./check_sonar_file_coverage.sh <file_path>

set -euo pipefail

SONAR_TOKEN="${SONAR_TOKEN:-}"
SONAR_ORG="${SONAR_ORG:-underpass-ai-swe-ai-fleet}"
SONAR_PROJECT="${SONAR_PROJECT:-underpass-ai-swe-ai-fleet}"
SONAR_HOST="${SONAR_HOST:-https://sonarcloud.io}"

if [ -z "$SONAR_TOKEN" ]; then
    echo "❌ Error: SONAR_TOKEN environment variable is required"
    exit 1
fi

FILE_PATH="${1:-services/backlog_review_processor/application/usecases/accumulate_deliberations_usecase.py}"

echo "🔍 Checking SonarCloud coverage for file: $FILE_PATH"
echo ""

# Get file measures
echo "📊 Fetching file coverage measures..."
curl -s -u "${SONAR_TOKEN}:" \
    "${SONAR_HOST}/api/measures/component?component=${SONAR_PROJECT}:${FILE_PATH}&metricKeys=coverage,new_coverage,lines_to_cover,uncovered_lines,new_lines_to_cover,new_uncovered_lines" \
    | jq '.' || echo "⚠️  Could not parse response"

echo ""
echo "📋 Fetching file issues (coverage-related)..."
curl -s -u "${SONAR_TOKEN}:" \
    "${SONAR_HOST}/api/issues/search?componentKeys=${SONAR_PROJECT}:${FILE_PATH}&types=CODE_SMELL&ps=5" \
    | jq '.issues[] | {message, line}' || echo "⚠️  No issues found"
