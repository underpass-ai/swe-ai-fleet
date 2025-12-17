#!/bin/bash
# Check SonarCloud coverage analysis
# This script connects to SonarCloud API to verify coverage data

set -euo pipefail

SONAR_TOKEN="${SONAR_TOKEN:-}"
SONAR_ORG="${SONAR_ORG:-underpass-ai-swe-ai-fleet}"
SONAR_PROJECT="${SONAR_PROJECT:-underpass-ai-swe-ai-fleet}"
SONAR_HOST="${SONAR_HOST:-https://sonarcloud.io}"

if [ -z "$SONAR_TOKEN" ]; then
    echo "❌ Error: SONAR_TOKEN environment variable is required"
    exit 1
fi

echo "🔍 Checking SonarCloud coverage for project: $SONAR_PROJECT"
echo ""

# Get project measures (coverage)
echo "📊 Fetching coverage measures..."
curl -s -u "${SONAR_TOKEN}:" \
    "${SONAR_HOST}/api/measures/component?component=${SONAR_PROJECT}&metricKeys=coverage,new_coverage,lines_to_cover,uncovered_lines" \
    | jq '.' || echo "⚠️  Could not parse response"

echo ""
echo "📊 Fetching new code coverage measures..."
curl -s -u "${SONAR_TOKEN}:" \
    "${SONAR_HOST}/api/measures/component?component=${SONAR_PROJECT}&metricKeys=new_coverage,new_lines_to_cover,new_uncovered_lines" \
    | jq '.' || echo "⚠️  Could not parse response"

echo ""
echo "📋 Fetching recent analysis..."
curl -s -u "${SONAR_TOKEN}:" \
    "${SONAR_HOST}/api/project_analyses/search?project=${SONAR_PROJECT}&ps=1" \
    | jq '.analyses[0] | {date, event}' || echo "⚠️  Could not parse response"
