"""Unit tests for CeremonyOutputSchemaValidator."""

import pytest

from core.ceremony_engine.domain.entities.ceremony_definition import CeremonyDefinition
from core.ceremony_engine.domain.value_objects import (
    Inputs,
    Output,
    Role,
    State,
    Step,
    StepHandlerType,
    StepId,
    Timeouts,
    Transition,
    TransitionTrigger,
)
from core.ceremony_engine.infrastructure.validators.ceremony_output_schema_validator import (
    CeremonyOutputSchemaValidator,
)


def _create_definition_with_output_schema(
    output_name: str, schema: dict[str, str] | None
) -> CeremonyDefinition:
    """Create a test ceremony definition with an output schema."""
    states = (
        State(id="STARTED", description="Started", initial=True, terminal=False),
        State(id="COMPLETED", description="Completed", initial=False, terminal=True),
    )
    transitions = (
        Transition(
            from_state="STARTED",
            to_state="COMPLETED",
            trigger=TransitionTrigger("complete"),
            guards=(),
            description="Complete",
        ),
    )
    steps = (
        Step(
            id=StepId("publish_results"),
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={"subject": "test.subject", "event_type": "test.event"},
        ),
    )
    outputs = {}
    if schema is not None:
        outputs[output_name] = Output(type="object", schema=schema)
    else:
        outputs[output_name] = Output(type="object", schema=None)

    return CeremonyDefinition(
        version="1.0",
        name="test_ceremony",
        description="Test ceremony",
        inputs=Inputs(required=(), optional=()),
        outputs=outputs,
        states=states,
        transitions=transitions,
        steps=steps,
        guards={},
        roles=(Role(id="SYSTEM", description="System", allowed_actions=()),),
        timeouts=Timeouts(step_default=60, step_max=3600, ceremony_max=86400),
        retry_policies={},
    )


class TestCeremonyOutputSchemaValidator:
    """Test cases for CeremonyOutputSchemaValidator."""

    def test_validate_skips_when_definition_is_none(self) -> None:
        """Test that validation is skipped when definition is None (backward compatibility)."""
        validator = CeremonyOutputSchemaValidator()
        step = Step(
            id=StepId("publish_results"),
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={"subject": "test.subject", "event_type": "test.event"},
        )
        payload = {"status": "ok"}

        # Should not raise any exception
        validator.validate(payload=payload, step=step, definition=None)

    def test_validate_skips_when_output_not_defined(self) -> None:
        """Test that validation is skipped when output is not defined for the step."""
        validator = CeremonyOutputSchemaValidator()
        definition = CeremonyDefinition(
            version="1.0",
            name="test_ceremony",
            description="Test ceremony",
            inputs=Inputs(required=(), optional=()),
            outputs={},  # No outputs defined
            states=(
                State(id="STARTED", description="Started", initial=True, terminal=False),
                State(id="COMPLETED", description="Completed", initial=False, terminal=True),
            ),
            transitions=(
                Transition(
                    from_state="STARTED",
                    to_state="COMPLETED",
                    trigger=TransitionTrigger("complete"),
                    guards=(),
                    description="Complete",
                ),
            ),
            steps=(
                Step(
                    id=StepId("publish_results"),
                    state="STARTED",
                    handler=StepHandlerType.PUBLISH_STEP,
                    config={"subject": "test.subject", "event_type": "test.event"},
                ),
            ),
            guards={},
            roles=(),
            timeouts=Timeouts(step_default=60, step_max=3600, ceremony_max=86400),
            retry_policies={},
        )
        step = Step(
            id=StepId("publish_results"),
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={"subject": "test.subject", "event_type": "test.event"},
        )
        payload = {"status": "ok"}

        # Should not raise any exception
        validator.validate(payload=payload, step=step, definition=definition)

    def test_validate_skips_when_schema_is_none(self) -> None:
        """Test that validation is skipped when output has no schema."""
        validator = CeremonyOutputSchemaValidator()
        definition = _create_definition_with_output_schema("publication", None)
        step = Step(
            id=StepId("publish_results"),
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={
                "subject": "test.subject",
                "event_type": "test.event",
                "output": "publication",
            },
        )
        payload = {"status": "ok"}

        # Should not raise any exception
        validator.validate(payload=payload, step=step, definition=definition)

    def test_validate_success_when_payload_matches_schema(self) -> None:
        """Test that validation succeeds when payload matches schema."""
        validator = CeremonyOutputSchemaValidator()
        schema = {
            "subject": "string",
            "event_type": "string",
            "status": "string",
        }
        definition = _create_definition_with_output_schema("publication", schema)
        step = Step(
            id=StepId("publish_results"),
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={
                "subject": "test.subject",
                "event_type": "test.event",
                "output": "publication",
            },
        )
        payload = {
            "subject": "test.subject",
            "event_type": "test.event",
            "status": "ok",
        }

        # Should not raise any exception
        validator.validate(payload=payload, step=step, definition=definition)

    def test_validate_rejects_missing_required_field(self) -> None:
        """Test that validation rejects payload missing required fields."""
        validator = CeremonyOutputSchemaValidator()
        schema = {
            "subject": "string",
            "event_type": "string",
            "status": "string",  # Required but missing in payload
        }
        definition = _create_definition_with_output_schema("publication", schema)
        step = Step(
            id=StepId("publish_results"),
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={
                "subject": "test.subject",
                "event_type": "test.event",
                "output": "publication",
            },
        )
        payload = {
            "subject": "test.subject",
            "event_type": "test.event",
            # Missing "status"
        }

        with pytest.raises(ValueError, match="missing required field: 'status'"):
            validator.validate(payload=payload, step=step, definition=definition)

    def test_validate_rejects_wrong_string_type(self) -> None:
        """Test that validation rejects payload with wrong string type."""
        validator = CeremonyOutputSchemaValidator()
        schema = {"name": "string"}
        definition = _create_definition_with_output_schema("publication", schema)
        step = Step(
            id=StepId("publish_results"),
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={"output": "publication"},
        )
        payload = {"name": 123}  # Should be string

        with pytest.raises(ValueError, match="must be a string"):
            validator.validate(payload=payload, step=step, definition=definition)

    def test_validate_rejects_wrong_number_type(self) -> None:
        """Test that validation rejects payload with wrong number type."""
        validator = CeremonyOutputSchemaValidator()
        schema = {"count": "number"}
        definition = _create_definition_with_output_schema("publication", schema)
        step = Step(
            id=StepId("publish_results"),
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={"output": "publication"},
        )
        payload = {"count": "not-a-number"}  # Should be number

        with pytest.raises(ValueError, match="must be a number"):
            validator.validate(payload=payload, step=step, definition=definition)

    def test_validate_accepts_int_as_number(self) -> None:
        """Test that validation accepts int as number type."""
        validator = CeremonyOutputSchemaValidator()
        schema = {"count": "number"}
        definition = _create_definition_with_output_schema("publication", schema)
        step = Step(
            id=StepId("publish_results"),
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={"output": "publication"},
        )
        payload = {"count": 42}  # int is valid number

        # Should not raise any exception
        validator.validate(payload=payload, step=step, definition=definition)

    def test_validate_accepts_float_as_number(self) -> None:
        """Test that validation accepts float as number type."""
        validator = CeremonyOutputSchemaValidator()
        schema = {"count": "number"}
        definition = _create_definition_with_output_schema("publication", schema)
        step = Step(
            id=StepId("publish_results"),
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={"output": "publication"},
        )
        payload = {"count": 3.14}  # float is valid number

        # Should not raise any exception
        validator.validate(payload=payload, step=step, definition=definition)

    def test_validate_rejects_wrong_boolean_type(self) -> None:
        """Test that validation rejects payload with wrong boolean type."""
        validator = CeremonyOutputSchemaValidator()
        schema = {"enabled": "boolean"}
        definition = _create_definition_with_output_schema("publication", schema)
        step = Step(
            id=StepId("publish_results"),
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={"output": "publication"},
        )
        payload = {"enabled": "true"}  # Should be boolean

        with pytest.raises(ValueError, match="must be a boolean"):
            validator.validate(payload=payload, step=step, definition=definition)

    def test_validate_accepts_boolean_type(self) -> None:
        """Test that validation accepts boolean type."""
        validator = CeremonyOutputSchemaValidator()
        schema = {"enabled": "boolean"}
        definition = _create_definition_with_output_schema("publication", schema)
        step = Step(
            id=StepId("publish_results"),
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={"output": "publication"},
        )
        payload = {"enabled": True}

        # Should not raise any exception
        validator.validate(payload=payload, step=step, definition=definition)

    def test_validate_rejects_wrong_object_type(self) -> None:
        """Test that validation rejects payload with wrong object type."""
        validator = CeremonyOutputSchemaValidator()
        schema = {"metadata": "object"}
        definition = _create_definition_with_output_schema("publication", schema)
        step = Step(
            id=StepId("publish_results"),
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={"output": "publication"},
        )
        payload = {"metadata": "not-an-object"}  # Should be dict

        with pytest.raises(ValueError, match="must be an object \\(dict\\)"):
            validator.validate(payload=payload, step=step, definition=definition)

    def test_validate_accepts_object_type(self) -> None:
        """Test that validation accepts object type."""
        validator = CeremonyOutputSchemaValidator()
        schema = {"metadata": "object"}
        definition = _create_definition_with_output_schema("publication", schema)
        step = Step(
            id=StepId("publish_results"),
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={"output": "publication"},
        )
        payload = {"metadata": {"key": "value"}}

        # Should not raise any exception
        validator.validate(payload=payload, step=step, definition=definition)

    def test_validate_rejects_wrong_array_type(self) -> None:
        """Test that validation rejects payload with wrong array type."""
        validator = CeremonyOutputSchemaValidator()
        schema = {"items": "array"}
        definition = _create_definition_with_output_schema("publication", schema)
        step = Step(
            id=StepId("publish_results"),
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={"output": "publication"},
        )
        payload = {"items": "not-an-array"}  # Should be list

        with pytest.raises(ValueError, match="must be an array \\(list\\)"):
            validator.validate(payload=payload, step=step, definition=definition)

    def test_validate_accepts_array_type(self) -> None:
        """Test that validation accepts array type."""
        validator = CeremonyOutputSchemaValidator()
        schema = {"items": "array"}
        definition = _create_definition_with_output_schema("publication", schema)
        step = Step(
            id=StepId("publish_results"),
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={"output": "publication"},
        )
        payload = {"items": [1, 2, 3]}

        # Should not raise any exception
        validator.validate(payload=payload, step=step, definition=definition)

    def test_validate_accepts_list_type_alias(self) -> None:
        """Test that validation accepts 'list' as alias for array type."""
        validator = CeremonyOutputSchemaValidator()
        schema = {"items": "list"}
        definition = _create_definition_with_output_schema("publication", schema)
        step = Step(
            id=StepId("publish_results"),
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={"output": "publication"},
        )
        payload = {"items": [1, 2, 3]}

        # Should not raise any exception
        validator.validate(payload=payload, step=step, definition=definition)

    def test_validate_rejects_non_dict_payload(self) -> None:
        """Test that validation rejects non-dict payload."""
        validator = CeremonyOutputSchemaValidator()
        schema = {"status": "string"}
        definition = _create_definition_with_output_schema("publication", schema)
        step = Step(
            id=StepId("publish_results"),
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={"output": "publication"},
        )
        payload = "not-a-dict"  # Should be dict

        with pytest.raises(ValueError, match="must be a dict"):
            validator.validate(payload=payload, step=step, definition=definition)  # type: ignore[arg-type]

    def test_validate_infers_output_name_from_step_id(self) -> None:
        """Test that validation infers output name from step.id when not in config."""
        validator = CeremonyOutputSchemaValidator()
        schema = {"status": "string"}
        # Output name "results" inferred from step.id "publish_results" -> "results"
        definition = _create_definition_with_output_schema("results", schema)
        step = Step(
            id=StepId("publish_results"),  # Will infer "results" from this
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={
                "subject": "test.subject",
                "event_type": "test.event",
                # No "output" in config - will infer from step.id
            },
        )
        payload = {"status": "ok"}

        # Should not raise any exception
        validator.validate(payload=payload, step=step, definition=definition)

    def test_validate_uses_explicit_output_name_from_config(self) -> None:
        """Test that validation uses explicit output name from step config."""
        validator = CeremonyOutputSchemaValidator()
        schema = {"status": "string"}
        definition = _create_definition_with_output_schema("publication", schema)
        step = Step(
            id=StepId("publish_results"),
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={
                "subject": "test.subject",
                "event_type": "test.event",
                "output": "publication",  # Explicit output name
            },
        )
        payload = {"status": "ok"}

        # Should not raise any exception
        validator.validate(payload=payload, step=step, definition=definition)

    def test_validate_complex_schema_with_multiple_types(self) -> None:
        """Test that validation works with complex schema containing multiple types."""
        validator = CeremonyOutputSchemaValidator()
        schema = {
            "subject": "string",
            "event_type": "string",
            "count": "number",
            "enabled": "boolean",
            "metadata": "object",
            "items": "array",
        }
        definition = _create_definition_with_output_schema("publication", schema)
        step = Step(
            id=StepId("publish_results"),
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={"output": "publication"},
        )
        payload = {
            "subject": "test.subject",
            "event_type": "test.event",
            "count": 42,
            "enabled": True,
            "metadata": {"key": "value"},
            "items": [1, 2, 3],
        }

        # Should not raise any exception
        validator.validate(payload=payload, step=step, definition=definition)

    def test_validate_type_case_insensitive(self) -> None:
        """Test that validation is case-insensitive for type names."""
        validator = CeremonyOutputSchemaValidator()
        schema = {
            "name": "STRING",  # Uppercase
            "count": "NUMBER",  # Uppercase
            "enabled": "BOOLEAN",  # Uppercase
        }
        definition = _create_definition_with_output_schema("publication", schema)
        step = Step(
            id=StepId("publish_results"),
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={"output": "publication"},
        )
        payload = {
            "name": "test",
            "count": 42,
            "enabled": True,
        }

        # Should not raise any exception
        validator.validate(payload=payload, step=step, definition=definition)

    def test_validate_type_aliases(self) -> None:
        """Test that validation accepts type aliases (str, int, float, bool, dict)."""
        validator = CeremonyOutputSchemaValidator()
        schema = {
            "name": "str",  # Alias for string
            "count": "int",  # Alias for number
            "price": "float",  # Alias for number
            "enabled": "bool",  # Alias for boolean
            "metadata": "dict",  # Alias for object
        }
        definition = _create_definition_with_output_schema("publication", schema)
        step = Step(
            id=StepId("publish_results"),
            state="STARTED",
            handler=StepHandlerType.PUBLISH_STEP,
            config={"output": "publication"},
        )
        payload = {
            "name": "test",
            "count": 42,
            "price": 3.14,
            "enabled": True,
            "metadata": {"key": "value"},
        }

        # Should not raise any exception
        validator.validate(payload=payload, step=step, definition=definition)
