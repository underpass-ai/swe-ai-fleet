#!/bin/bash
#
# Serve Proto Documentation
#
# Serves generated proto documentation via a local HTTP server.
# Auto-generates docs if needed, then starts a development server.
#
# Usage:
#   ./scripts/specs/serve-docs.sh              # Serve on localhost:8080
#   ./scripts/specs/serve-docs.sh --port=3000  # Custom port
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Defaults
PORT="${PORT:-8080}"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --port=*)
      PORT="${1#*=}"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--port=<port>]"
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SPECS_DIR="$PROJECT_ROOT/specs"
DOCS_DIR="$SPECS_DIR/docs/api"

cd "$SPECS_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Proto Documentation Server${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Generate docs if they don't exist
if [ ! -d "$DOCS_DIR" ] || [ ! -f "$DOCS_DIR/README.md" ]; then
    echo -e "${BLUE}Generating documentation...${NC}"
    "$SCRIPT_DIR/generate-docs.sh" || {
        echo -e "${YELLOW}⚠️  Could not generate docs${NC}"
    }
fi

# Check if docs exist
if [ ! -d "$DOCS_DIR" ]; then
    echo -e "${RED}❌ Documentation directory not found: $DOCS_DIR${NC}"
    echo ""
    echo "Generate docs first:"
    echo "  ./scripts/specs/generate-docs.sh"
    exit 1
fi

# Start server
echo -e "${BLUE}Starting documentation server...${NC}"
echo ""
echo -e "${GREEN}Documentation available at:${NC}"
echo -e "  ${BLUE}http://localhost:${PORT}${NC}"
echo ""
echo -e "${GREEN}Services:${NC}"
for service in context orchestrator ray_executor planning storycoach workspace; do
    if [ -f "$DOCS_DIR/${service}.md" ]; then
        echo -e "  ${BLUE}http://localhost:${PORT}/${service}.md${NC}"
    fi
done
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Serve with Python
cd "$DOCS_DIR"
python3 -m http.server "$PORT"



