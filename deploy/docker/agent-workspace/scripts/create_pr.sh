#!/bin/bash
# Helper script to create/update PR

set -e

if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_TOKEN must be set"
    exit 1
fi

BRANCH="${GIT_BRANCH:-$(git branch --show-current)}"
BASE="${PR_BASE:-main}"
TITLE="${PR_TITLE:-Automated changes from agent}"
BODY="${PR_BODY:-This PR was created automatically by the SWE AI Fleet agent.}"

echo "=== Creating/Updating Pull Request ==="
echo "Branch: $BRANCH"
echo "Base: $BASE"

# Check if PR already exists
PR_NUMBER=$(gh pr list --head "$BRANCH" --json number --jq '.[0].number' 2>/dev/null || echo "")

if [ -n "$PR_NUMBER" ]; then
    echo "Updating existing PR #$PR_NUMBER"
    gh pr edit "$PR_NUMBER" --body "$BODY"
else
    echo "Creating new PR"
    gh pr create --title "$TITLE" --body "$BODY" --base "$BASE" --head "$BRANCH"
fi

echo "=== PR Complete ==="



