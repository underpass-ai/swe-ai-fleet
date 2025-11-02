#!/bin/bash
# Increment version script

set -e

MAKEFILE="Makefile"

if [ ! -f "$MAKEFILE" ]; then
    echo "❌ Makefile not found"
    exit 1
fi

# Extract current version
CURRENT=$(grep "^VERSION ?=" "$MAKEFILE" | cut -d'=' -f2 | tr -d ' ')

echo "Current version: $CURRENT"

# Parse version
if [[ $CURRENT =~ ^v([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
    MAJOR="${BASH_REMATCH[1]}"
    MINOR="${BASH_REMATCH[2]}"
    PATCH="${BASH_REMATCH[3]}"
    
    # Increment patch
    PATCH=$((PATCH + 1))
    NEW_VERSION="v${MAJOR}.${MINOR}.${PATCH}"
    
    # Update Makefile
    sed -i "s/^VERSION ?=.*/VERSION ?= $NEW_VERSION/" "$MAKEFILE"
    
    echo "✅ Version incremented to: $NEW_VERSION"
else
    echo "❌ Invalid version format: $CURRENT"
    exit 1
fi

