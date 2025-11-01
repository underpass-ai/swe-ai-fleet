#!/bin/bash
#
# Generate API Documentation from Protobuf Files
#
# Generates markdown documentation from proto definitions.
# Outputs readable markdown files for the API contracts.
#
# Usage:
#   ./scripts/specs/generate-docs.sh                 # Generate to docs/api/
#   ./scripts/specs/generate-docs.sh --output=./docs # Custom output
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
OUTPUT_DIR="${OUTPUT_DIR:-docs/api}"

while [[ $# -gt 0 ]]; do
  case $1 in
    --output=*)
      OUTPUT_DIR="${1#*=}"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--output=<path>]"
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SPECS_DIR="$PROJECT_ROOT/specs"

cd "$SPECS_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}API Documentation Generation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Create simple markdown docs for each service
echo -e "${BLUE}Generating markdown documentation...${NC}"

for service in context orchestrator ray_executor planning storycoach workspace; do
    if [ -f "fleet/${service}/v1/${service}.proto" ]; then
        SERVICE_NAME=$(echo "$service" | sed 's/_/ /g' | sed 's/\b\w/\u&/g')
        echo -e "  ${BLUE}→ $service${NC}"
        
        cat > "$OUTPUT_DIR/${service}.md" << EOF
# ${SERVICE_NAME} Service API

**Package**: \`fleet.${service}.v1\`  
**Version**: v1  
**Generated**: $(date -u +"%Y-%m-%d")

---

## Full Protocol Definition

<details>
<summary>Click to expand full proto definition</summary>

\`\`\`protobuf
$(cat "fleet/${service}/v1/${service}.proto")
\`\`\`

</details>

---

## Quick Start

\`\`\`python
from fleet.${service}.v1 import ${service}_pb2, ${service}_pb2_grpc
\`\`\`

\`\`\`go
import "github.com/underpass-ai/swe-ai-fleet/gen/fleet/${service}/v1"
\`\`\`

---

*This documentation is auto-generated from \`specs/fleet/${service}/v1/${service}.proto\`*
EOF
    fi
done

echo ""
echo -e "${GREEN}✓ Markdown documentation generated${NC}"
echo ""

# Generate index
cat > "$OUTPUT_DIR/README.md" << 'EOF'
# SWE AI Fleet - API Documentation

This directory contains auto-generated API documentation from Protocol Buffer definitions.

## Services

- [Context Service](context.md) - Decision graph and timeline management
- [Orchestrator Service](orchestrator.md) - Multi-agent deliberation coordination
- [Ray Executor Service](ray_executor.md) - Distributed task execution
- [Planning Service](planning.md) - User story and workflow management
- [StoryCoach Service](storycoach.md) - Story refinement and validation
- [Workspace Service](workspace.md) - Code evaluation and rigor assessment

## Version

Current API version: v1.0.0

## How to Read

Each service has its own markdown file. Expand the details section to view the complete proto definition.

## More Information

- [API Versioning Strategy](../../docs/API_VERSIONING_STRATEGY.md)
- [Full Repository](../../README.md)
- [Proto Versioning Guide](../../docs/specs/PROTO_VERSIONING_GUIDE.md)
EOF

echo -e "${GREEN}✓ Index created${NC}"
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ API Documentation generated${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Output: $OUTPUT_DIR"
echo ""
echo "View with:"
echo "  # Option 1: Serve locally"
echo "  python3 -m http.server 8080 --directory $OUTPUT_DIR"
echo "  # Open: http://localhost:8080"
echo ""
echo "  # Option 2: Open in editor"
echo "  cat $OUTPUT_DIR/orchestrator.md | less"
echo ""
echo "  # Option 3: View on GitHub"
echo "  # Files are automatically rendered as markdown"
