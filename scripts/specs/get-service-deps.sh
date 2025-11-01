#!/bin/bash
#
# Get Service Proto Dependencies
#
# Reads dependencies.yaml to determine which proto bundles a service needs.
# Used by Dockerfiles to generate the correct proto loading commands.
#
# Usage:
#   ./scripts/specs/get-service-deps.sh orchestrator
#   ./scripts/specs/get-service-deps.sh orchestrator --format=json
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

if [ $# -eq 0 ]; then
    echo "Usage: $0 <service-name> [--format=json]"
    exit 1
fi

SERVICE="$1"
FORMAT="${FORMAT:-text}"

while [[ $# -gt 1 ]]; do
    case "$2" in
        --format=*)
            FORMAT="${2#*=}"
            shift
            ;;
        *)
            echo "Unknown option: $2"
            exit 1
            ;;
    esac
    shift
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPS_FILE="$PROJECT_ROOT/specs/dependencies.yaml"

if [ ! -f "$DEPS_FILE" ]; then
    echo -e "${RED}❌ dependencies.yaml not found${NC}"
    exit 1
fi

# Check if yq is available for YAML parsing
if command -v yq &> /dev/null; then
    # Use yq if available
    VERSION=$(yq eval ".services.$SERVICE.version // .default_version" "$DEPS_FILE")
    REQUIRED=$(yq eval -o csv ".services.$SERVICE.required[]" "$DEPS_FILE")
    
    if [ "$FORMAT" = "json" ]; then
        echo "{\"version\":\"$VERSION\",\"required\":[$(echo $REQUIRED | sed 's/ /","/g')]}"
    else
        echo "$VERSION"
        echo "$REQUIRED"
    fi
elif command -v python3 &> /dev/null; then
    # Fallback to Python
    python3 << EOF
import yaml
import sys
import json

with open("$DEPS_FILE", "r") as f:
    deps = yaml.safe_load(f)

if "$SERVICE" not in deps.get("services", {}):
    print(f"Service not found: $SERVICE", file=sys.stderr)
    sys.exit(1)

service = deps["services"]["$SERVICE"]
version = service.get("version", deps.get("default_version"))
required = service.get("required", [])

if "$FORMAT" == "json":
    print(json.dumps({"version": version, "required": required}))
else:
    print(version)
    print(" ".join(required))
EOF
else
    echo -e "${RED}❌ Neither yq nor python3 available for YAML parsing${NC}"
    echo ""
    echo "Install yq:"
    echo "  sudo pacman -S yq"
    exit 1
fi



