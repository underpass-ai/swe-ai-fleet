#!/bin/bash
# Helper script to run SonarQube analysis

set -e

if [ -z "$SONAR_HOST_URL" ] || [ -z "$SONAR_TOKEN" ] || [ -z "$SONAR_PROJECT_KEY" ]; then
    echo "Error: SONAR_HOST_URL, SONAR_TOKEN, and SONAR_PROJECT_KEY must be set"
    exit 1
fi

echo "=== Running SonarQube Analysis ==="

sonar-scanner \
    -Dsonar.projectKey="$SONAR_PROJECT_KEY" \
    -Dsonar.sources=. \
    -Dsonar.host.url="$SONAR_HOST_URL" \
    -Dsonar.login="$SONAR_TOKEN"

echo "=== SonarQube Analysis Complete ==="



