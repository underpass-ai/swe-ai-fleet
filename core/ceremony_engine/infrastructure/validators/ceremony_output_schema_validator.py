"""CeremonyOutputSchemaValidator: Validates payloads against ceremony output schemas.

Following Hexagonal Architecture:
- This is infrastructure (validator)
- Validates payload structure against ceremony definition output schemas
- Fail-fast validation on all errors
"""

from typing import Any

from core.ceremony_engine.domain.entities.ceremony_definition import CeremonyDefinition
from core.ceremony_engine.domain.value_objects.step import Step


class CeremonyOutputSchemaValidator:
    """Validates payloads against output schemas defined in ceremony definitions for steps.

    This validator:
    - Extracts output schema from ceremony definition
    - Validates payload structure and types
    - Provides clear error messages for validation failures

    Following Hexagonal Architecture:
    - This is infrastructure (validator)
    - No domain dependencies beyond value objects
    - Fail-fast validation
    """

    def validate(
        self,
        payload: dict[str, Any],
        step: Step,
        definition: CeremonyDefinition | None,
    ) -> None:
        """Validate payload against output schema if defined.

        Args:
            payload: Payload to validate
            step: Step being executed (used to find output name)
            definition: Ceremony definition containing output schemas (None to skip validation)

        Raises:
            ValueError: If payload does not match schema
        """
        # Skip validation if definition not provided (backward compatibility)
        if definition is None:
            return
        # Get output name from step config, or infer from step.id
        output_name = step.config.get("output")
        if not output_name:
            # Try to infer from step.id (e.g., "publish_results" -> "results")
            # This is a convention, not a requirement
            output_name = step.id.value.replace("publish_", "").replace("_", "")

        # Get output specification
        output_spec = definition.outputs.get(output_name)
        if not output_spec:
            # No output defined for this step - skip validation
            return

        # If schema is defined, validate payload
        if output_spec.schema:
            self._validate_payload_against_schema(
                payload=payload,
                schema=output_spec.schema,
                output_name=output_name,
                step_id=step.id.value,
            )

    def _validate_payload_against_schema(
        self,
        payload: dict[str, Any],
        schema: dict[str, Any],
        output_name: str,
        step_id: str,
    ) -> None:
        """Validate payload structure against schema.

        Schema format:
        - Keys in schema represent required fields
        - Values represent expected types: "string", "number", "boolean", "object", "array", "list"

        Args:
            payload: Payload to validate
            schema: Schema definition
            output_name: Output name (for error messages)
            step_id: Step ID (for error messages)

        Raises:
            ValueError: If payload does not match schema
        """
        if not isinstance(payload, dict):
            raise ValueError(
                f"Payload for output '{output_name}' (step '{step_id}') must be a dict, "
                f"got {type(payload)}"
            )

        # Validate required fields from schema
        for field_name, expected_type in schema.items():
            if field_name not in payload:
                raise ValueError(
                    f"Payload for output '{output_name}' (step '{step_id}') missing required field: '{field_name}'"
                )

            field_value = payload[field_name]
            self._validate_field_type(
                field_name=field_name,
                field_value=field_value,
                expected_type=expected_type,
                output_name=output_name,
                step_id=step_id,
            )

    def _validate_field_type(
        self,
        field_name: str,
        field_value: Any,
        expected_type: str,
        output_name: str,
        step_id: str,
    ) -> None:
        """Validate a field value matches expected type.

        Args:
            field_name: Name of the field
            field_value: Value to validate
            expected_type: Expected type (string, number, boolean, object, array, list)
            output_name: Output name (for error messages)
            step_id: Step ID (for error messages)

        Raises:
            ValueError: If field type does not match
        """
        type_lower = expected_type.lower().strip()

        if type_lower in ("string", "str"):
            if not isinstance(field_value, str):
                raise ValueError(
                    f"Field '{field_name}' in output '{output_name}' (step '{step_id}') "
                    f"must be a string, got {type(field_value)}"
                )

        elif type_lower in ("number", "int", "float"):
            if not isinstance(field_value, (int, float)):
                raise ValueError(
                    f"Field '{field_name}' in output '{output_name}' (step '{step_id}') "
                    f"must be a number, got {type(field_value)}"
                )

        elif type_lower in ("boolean", "bool"):
            if not isinstance(field_value, bool):
                raise ValueError(
                    f"Field '{field_name}' in output '{output_name}' (step '{step_id}') "
                    f"must be a boolean, got {type(field_value)}"
                )

        elif type_lower in ("object", "dict"):
            if not isinstance(field_value, dict):
                raise ValueError(
                    f"Field '{field_name}' in output '{output_name}' (step '{step_id}') "
                    f"must be an object (dict), got {type(field_value)}"
                )

        elif type_lower in ("array", "list"):
            if not isinstance(field_value, list):
                raise ValueError(
                    f"Field '{field_name}' in output '{output_name}' (step '{step_id}') "
                    f"must be an array (list), got {type(field_value)}"
                )
