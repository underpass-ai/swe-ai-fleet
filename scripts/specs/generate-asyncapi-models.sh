#!/bin/bash
#
# Generate Python dataclasses from AsyncAPI specification
#
# Generates dataclasses for NATS message payloads from asyncapi.yaml
# Outputs to core/nats/gen/ for shared use across services
#
# Usage:
#   ./scripts/specs/generate-asyncapi-models.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Determine project root - works both locally and in Docker
# If running in Docker, assume we're at /app or /build
if [ -d "/app" ] && [ -f "/app/specs/asyncapi.yaml" ]; then
    # Running in Docker (final stage)
    PROJECT_ROOT="/app"
elif [ -d "/build" ] && [ -f "/build/specs/asyncapi.yaml" ]; then
    # Running in Docker (builder stage)
    PROJECT_ROOT="/build"
else
    # Running locally
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

SPECS_DIR="$PROJECT_ROOT/specs"
ASYNCAPI_FILE="$SPECS_DIR/asyncapi.yaml"
OUTPUT_DIR="$PROJECT_ROOT/core/nats/gen"

cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}AsyncAPI Code Generation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if asyncapi.yaml exists
if [ ! -f "$ASYNCAPI_FILE" ]; then
    echo -e "${RED}❌ AsyncAPI file not found: $ASYNCAPI_FILE${NC}"
    exit 1
fi

# Check if datamodel-code-generator is installed
if ! python -m datamodel_code_generator --version >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  datamodel-code-generator not found. Installing...${NC}"
    pip install datamodel-code-generator
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo -e "${BLUE}Generating Python dataclasses from AsyncAPI...${NC}"
echo -e "  Input: ${ASYNCAPI_FILE}"
echo -e "  Output: ${OUTPUT_DIR}"
echo ""

# Generate dataclasses from AsyncAPI using Python script
python3 << 'PYTHON_SCRIPT'
import yaml
import json
from pathlib import Path
import subprocess
import sys

# Load AsyncAPI spec
specs_dir = Path("specs")
asyncapi_file = specs_dir / "asyncapi.yaml"
output_dir = Path("core/nats/gen")
output_dir.mkdir(parents=True, exist_ok=True)

print("📦 Loading AsyncAPI specification...")
with open(asyncapi_file, 'r') as f:
    asyncapi = yaml.safe_load(f)

# Extract schemas
schemas = asyncapi.get('components', {}).get('schemas', {})

# Generate AgentResponsePayload
print("📦 Generating AgentResponsePayload...")
agent_response_payload = schemas.get('AgentResponsePayload', {})
if agent_response_payload:
    # Create JSON Schema format for datamodel-code-generator
    json_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "title": "AgentResponsePayload",
        "description": agent_response_payload.get('description', ''),
        "properties": agent_response_payload.get('properties', {}),
        "required": agent_response_payload.get('required', [])
    }

    # Write temporary JSON schema
    temp_schema = output_dir / "agent_response_payload_schema.json"
    with open(temp_schema, 'w') as f:
        json.dump(json_schema, f, indent=2)

    # Generate dataclass
    output_file = output_dir / "agent_response_payload.py"
    result = subprocess.run([
        sys.executable, "-m", "datamodel_code_generator",
        "--input", str(temp_schema),
        "--output", str(output_file),
        "--output-model-type", "dataclasses.dataclass",
        "--use-annotated",
        "--use-standard-collections",
        "--use-schema-description",
        "--field-constraints",
        "--snake-case-field",
        "--disable-timestamp",
        "--use-generic-container-types"
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Error generating AgentResponsePayload: {result.stderr}")
        sys.exit(1)

    # Clean up temp schema
    temp_schema.unlink()

    # Fix imports in generated file
    if output_file.exists():
        content = output_file.read_text()
        # Ensure proper imports
        if "from dataclasses import dataclass" not in content:
            content = "from dataclasses import dataclass\nfrom typing import Any, Optional\n\n" + content
        output_file.write_text(content)
        print(f"✅ Generated: {output_file}")
    else:
        print("❌ Output file not created")
        sys.exit(1)
else:
    print("❌ AgentResponsePayload schema not found")

# Create __init__.py
init_file = output_dir / "__init__.py"
init_file.write_text('"""Generated NATS message payloads from AsyncAPI specification."""\n\nfrom .agent_response_payload import AgentResponsePayload\n\n__all__ = ["AgentResponsePayload"]\n')
print(f"✅ Created: {init_file}")

print("\n✅ AsyncAPI code generation complete!")
PYTHON_SCRIPT

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Success!${NC}"
    echo -e "   Generated files in: ${OUTPUT_DIR}"
else
    echo -e "${RED}❌ Generation failed${NC}"
    exit 1
fi



