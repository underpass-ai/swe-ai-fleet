#!/usr/bin/env python3
"""Generate Python dataclasses from AsyncAPI specification.

Generates dataclasses for NATS message payloads from asyncapi.yaml
Outputs to backlog_review_processor/gen/ (service-specific)

Usage:
    python services/backlog_review_processor/scripts/generate_asyncapi_models.py
"""

import json
import subprocess
import sys
from pathlib import Path

import yaml


def determine_project_root() -> Path:
    """Determine project root - works both locally and in Docker."""
    # If running in Docker, assume we're at /app or /build
    if Path("/build").exists() and Path("/build/specs/asyncapi.yaml").exists():
        # Running in Docker (builder stage)
        return Path("/build")
    elif Path("/app").exists() and Path("/app/specs/asyncapi.yaml").exists():
        # Running in Docker (final stage)
        return Path("/app")
    else:
        # Running locally - go up from scripts/ to service/ to project root
        script_dir = Path(__file__).parent
        service_dir = script_dir.parent
        return service_dir.parent.parent


def main() -> None:
    """Generate Python dataclasses from AsyncAPI specification."""
    project_root = determine_project_root()
    specs_dir = project_root / "specs"
    asyncapi_file = specs_dir / "asyncapi.yaml"
    output_dir = project_root / "backlog_review_processor" / "gen"

    # Check if asyncapi.yaml exists
    if not asyncapi_file.exists():
        print(f"❌ AsyncAPI file not found: {asyncapi_file}", file=sys.stderr)
        sys.exit(1)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    print("📦 Loading AsyncAPI specification...")
    with open(asyncapi_file, "r") as f:
        asyncapi = yaml.safe_load(f)

    # Extract schemas
    schemas = asyncapi.get("components", {}).get("schemas", {})

    # Generate AgentResponsePayload
    print("📦 Generating AgentResponsePayload...")
    agent_response_payload = schemas.get("AgentResponsePayload", {})
    if agent_response_payload:
        # Create JSON Schema format for datamodel-code-generator
        json_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": "AgentResponsePayload",
            "description": agent_response_payload.get("description", ""),
            "properties": agent_response_payload.get("properties", {}),
            "required": agent_response_payload.get("required", []),
        }

        # Write temporary JSON schema
        temp_schema = output_dir / "agent_response_payload_schema.json"
        with open(temp_schema, "w") as f:
            json.dump(json_schema, f, indent=2)

        # Generate dataclass
        output_file = output_dir / "agent_response_payload.py"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "datamodel_code_generator",
                "--input",
                str(temp_schema),
                "--output",
                str(output_file),
                "--output-model-type",
                "dataclasses.dataclass",
                "--use-annotated",
                "--use-standard-collections",
                "--use-schema-description",
                "--field-constraints",
                "--snake-case-field",
                "--disable-timestamp",
                "--use-generic-container-types",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"❌ Error generating AgentResponsePayload: {result.stderr}", file=sys.stderr)
            sys.exit(1)

        # Clean up temp schema
        temp_schema.unlink()

        # Fix imports in generated file
        if output_file.exists():
            content = output_file.read_text()
            # Ensure proper imports
            if "from dataclasses import dataclass" not in content:
                content = (
                    "from dataclasses import dataclass\nfrom typing import Any, Optional\n\n" + content
                )
            output_file.write_text(content)
            print(f"✅ Generated: {output_file}")
        else:
            print("❌ Output file not created", file=sys.stderr)
            sys.exit(1)
    else:
        print("❌ AgentResponsePayload schema not found", file=sys.stderr)
        sys.exit(1)

    # Create __init__.py
    init_file = output_dir / "__init__.py"
    init_file.write_text(
        '"""Generated NATS message payloads from AsyncAPI specification."""\n\n'
        "from .agent_response_payload import AgentResponsePayload\n\n"
        '__all__ = ["AgentResponsePayload"]\n'
    )
    print(f"✅ Created: {init_file}")

    print("\n✅ AsyncAPI code generation complete!")


if __name__ == "__main__":
    main()
