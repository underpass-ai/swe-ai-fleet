#!/bin/bash
# Auto-increment version for test-system-e2e

VERSION_FILE=".version"

if [ ! -f "$VERSION_FILE" ]; then
    echo "0.0.1" > "$VERSION_FILE"
    cat "$VERSION_FILE"
else
    current=$(cat "$VERSION_FILE")
    echo "$current" | awk -F. '{print $1"."$2"."($3+1)}' > "$VERSION_FILE"
    cat "$VERSION_FILE"
fi

