"""Contract tests for CeremonyRunner event payloads.

These tests ensure that event payloads published by CeremonyRunner
conform to the schemas defined in specs/asyncapi.yaml.

Following contract testing principles:
- Load schemas from asyncapi.yaml
- Validate payloads against schemas
- Test both ceremony.step.executed and ceremony.transition.applied events
- Verify required fields, types, and enum values
"""

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest
import yaml
from jsonschema import Draft202012Validator, ValidationError

from core.ceremony_engine.application.ports.messaging_port import MessagingPort
from core.ceremony_engine.application.ports.persistence_port import PersistencePort
from core.ceremony_engine.application.ports.step_handler_port import StepHandlerPort
from core.ceremony_engine.application.services.ceremony_runner import CeremonyRunner
from core.ceremony_engine.domain.entities.ceremony_definition import CeremonyDefinition
from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance
from core.ceremony_engine.domain.value_objects import (
    ContextEntry,
    ContextKey,
    ExecutionContext,
    Role,
    State,
    Step,
    StepHandlerType,
    StepId,
    StepResult,
    StepStatus,
    StepStatusMap,
    StepStatusEntry,
    StepOutputMap,
    Timeouts,
    Transition,
    TransitionTrigger,
)
from core.shared.idempotency.idempotency_port import IdempotencyPort


def _load_asyncapi_schema() -> dict[str, Any]:
    """Load asyncapi.yaml and return the full specification."""
    # Find project root using resolved absolute path
    # From: core/ceremony_engine/tests/unit/application/services/test_ceremony_runner_contract.py
    # Navigate: services -> application -> unit -> tests -> ceremony_engine -> core -> root
    current = Path(__file__).resolve()
    project_root = current.parents[6]  # Go up 6 levels to reach project root
    asyncapi_file = project_root / "specs" / "asyncapi.yaml"
    
    if not asyncapi_file.exists():
        pytest.skip(f"asyncapi.yaml not found at {asyncapi_file}")
    
    with open(asyncapi_file, "r") as f:
        return yaml.safe_load(f)


def _get_payload_schema(schema_name: str) -> dict[str, Any]:
    """Extract a payload schema from asyncapi.yaml.
    
    Args:
        schema_name: Name of the schema (e.g., "CeremonyStepExecutedPayload")
        
    Returns:
        Schema definition dict
    """
    asyncapi = _load_asyncapi_schema()
    schemas = asyncapi.get("components", {}).get("schemas", {})
    
    if schema_name not in schemas:
        pytest.fail(f"Schema {schema_name} not found in asyncapi.yaml")
    
    return schemas[schema_name]


def _validate_payload(payload: dict[str, Any], schema: dict[str, Any]) -> None:
    """Validate payload against schema.
    
    Args:
        payload: Payload to validate
        schema: JSON Schema definition
        
    Raises:
        ValidationError: If payload does not conform to schema
    """
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(payload))
    
    if errors:
        error_messages = []
        for error in errors:
            error_messages.append(
                f"  - {error.json_path}: {error.message}"
            )
        raise ValidationError(
            f"Payload validation failed:\n" + "\n".join(error_messages)
        )


def create_test_definition() -> CeremonyDefinition:
    """Create a test ceremony definition."""
    from core.ceremony_engine.domain.value_objects import Guard, GuardName, GuardType, Inputs
    
    states = (
        State(id="STARTED", description="Started", initial=True, terminal=False),
        State(id="PROCESSING", description="Processing", initial=False, terminal=False),
        State(id="COMPLETED", description="Completed", initial=False, terminal=True),
    )
    
    steps = (
        Step(
            id=StepId("test_step"),
            state="STARTED",
            handler=StepHandlerType.DELIBERATION_STEP,
            config={"agent_role": "ARCHITECT"},
        ),
    )
    
    transitions = (
        Transition(
            from_state="STARTED",
            to_state="PROCESSING",
            trigger=TransitionTrigger("step_completed"),
            description="Transition from STARTED to PROCESSING",
            guards=(),
        ),
    )
    
    roles = (
        Role(
            id="ADMIN",
            description="Administrator role",
            allowed_actions=("test_step", "step_completed"),
        ),
    )
    
    return CeremonyDefinition(
        version="1.0",
        name="test_ceremony",
        description="Test ceremony for contract tests",
        inputs=Inputs(required=(), optional=()),
        outputs={},
        states=states,
        steps=steps,
        transitions=transitions,
        guards={},
        roles=roles,
        timeouts=Timeouts(step_default=300, step_max=600, ceremony_max=3600),
        retry_policies={},
    )


def create_test_instance(definition: CeremonyDefinition) -> CeremonyInstance:
    """Create a test ceremony instance."""
    from datetime import datetime, UTC
    
    return CeremonyInstance(
        instance_id="inst-123",
        definition=definition,
        current_state="STARTED",
        step_status=StepStatusMap(
            entries=(
                StepStatusEntry(
                    step_id=StepId("test_step"),
                    status=StepStatus.PENDING,
                ),
            )
        ),
        correlation_id="corr-123",
        idempotency_keys=frozenset(),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        step_outputs=StepOutputMap(entries=()),
    )


@pytest.mark.asyncio
async def test_ceremony_step_executed_payload_conforms_to_schema() -> None:
    """Test that ceremony.step.executed payload conforms to asyncapi.yaml schema."""
    schema = _get_payload_schema("CeremonyStepExecutedPayload")
    
    definition = create_test_definition()
    instance = create_test_instance(definition)
    
    # Mock step handler
    step_handler_port = AsyncMock(spec=StepHandlerPort)
    step_handler_port.execute_step.return_value = StepResult(
        status=StepStatus.COMPLETED,
        output={"result": "success", "data": {"key": "value"}},
    )
    
    # Mock persistence
    persistence_port = AsyncMock(spec=PersistencePort)
    
    # Capture published events
    published_events: list[dict[str, Any]] = []
    
    async def capture_publish(subject: str, envelope: Any) -> None:
        """Capture published event envelope."""
        published_events.append({
            "subject": subject,
            "payload": envelope.payload,
        })
    
    messaging_port = AsyncMock(spec=MessagingPort)
    messaging_port.publish_event.side_effect = capture_publish
    
    runner = CeremonyRunner(
        step_handler_port=step_handler_port,
        messaging_port=messaging_port,
        persistence_port=persistence_port,
    )
    
    # Execute step
    await runner.execute_step(instance, StepId("test_step"))
    
    # Find step.executed event
    step_executed_events = [
        event for event in published_events
        if event["subject"] == "ceremony.step.executed"
    ]
    
    assert len(step_executed_events) == 1, "Expected exactly one ceremony.step.executed event"
    
    payload = step_executed_events[0]["payload"]
    
    # Validate payload against schema
    _validate_payload(payload, schema)
    
    # Additional assertions
    assert payload["instance_id"] == "inst-123"
    assert payload["step_id"] == "test_step"
    assert payload["status"] in ["COMPLETED", "FAILED", "CANCELLED"]
    # Note: current_state may be STARTED or PROCESSING depending on whether transition was applied
    assert payload["current_state"] in ["STARTED", "PROCESSING"]
    assert isinstance(payload["output"], dict)


@pytest.mark.asyncio
async def test_ceremony_step_executed_payload_with_error_message() -> None:
    """Test that ceremony.step.executed payload with error_message conforms to schema."""
    schema = _get_payload_schema("CeremonyStepExecutedPayload")
    
    definition = create_test_definition()
    instance = create_test_instance(definition)
    
    # Mock step handler to return failure
    step_handler_port = AsyncMock(spec=StepHandlerPort)
    step_handler_port.execute_step.return_value = StepResult(
        status=StepStatus.FAILED,
        output={},
        error_message="Step execution failed",
    )
    
    # Mock persistence
    persistence_port = AsyncMock(spec=PersistencePort)
    
    # Capture published events
    published_events: list[dict[str, Any]] = []
    
    async def capture_publish(subject: str, envelope: Any) -> None:
        """Capture published event envelope."""
        published_events.append({
            "subject": subject,
            "payload": envelope.payload,
        })
    
    messaging_port = AsyncMock(spec=MessagingPort)
    messaging_port.publish_event.side_effect = capture_publish
    
    runner = CeremonyRunner(
        step_handler_port=step_handler_port,
        messaging_port=messaging_port,
        persistence_port=persistence_port,
    )
    
    # Execute step (will fail)
    await runner.execute_step(instance, StepId("test_step"))
    
    # Find step.executed event
    step_executed_events = [
        event for event in published_events
        if event["subject"] == "ceremony.step.executed"
    ]
    
    assert len(step_executed_events) == 1
    
    payload = step_executed_events[0]["payload"]
    
    # Validate payload against schema
    _validate_payload(payload, schema)
    
    # Verify error_message is present for FAILED status
    assert payload["status"] == "FAILED"
    assert "error_message" in payload
    assert payload["error_message"] == "Step execution failed"


@pytest.mark.asyncio
async def test_ceremony_transition_applied_payload_conforms_to_schema() -> None:
    """Test that ceremony.transition.applied payload conforms to asyncapi.yaml schema."""
    schema = _get_payload_schema("CeremonyTransitionAppliedPayload")
    
    definition = create_test_definition()
    instance = create_test_instance(definition)
    
    # Mock step handler
    step_handler_port = AsyncMock(spec=StepHandlerPort)
    step_handler_port.execute_step.return_value = StepResult(
        status=StepStatus.COMPLETED,
        output={},
    )
    
    # Mock persistence
    persistence_port = AsyncMock(spec=PersistencePort)
    
    # Capture published events
    published_events: list[dict[str, Any]] = []
    
    async def capture_publish(subject: str, envelope: Any) -> None:
        """Capture published event envelope."""
        published_events.append({
            "subject": subject,
            "payload": envelope.payload,
        })
    
    messaging_port = AsyncMock(spec=MessagingPort)
    messaging_port.publish_event.side_effect = capture_publish
    
    runner = CeremonyRunner(
        step_handler_port=step_handler_port,
        messaging_port=messaging_port,
        persistence_port=persistence_port,
    )
    
    # Execute step (will trigger transition)
    await runner.execute_step(instance, StepId("test_step"))
    
    # Find transition.applied event
    transition_events = [
        event for event in published_events
        if event["subject"] == "ceremony.transition.applied"
    ]
    
    assert len(transition_events) >= 1, "Expected at least one ceremony.transition.applied event"
    
    payload = transition_events[0]["payload"]
    
    # Validate payload against schema
    _validate_payload(payload, schema)
    
    # Additional assertions
    assert payload["instance_id"] == "inst-123"
    assert payload["from_state"] == "STARTED"
    assert payload["to_state"] == "PROCESSING"
    assert payload["trigger"] == "step_completed"


@pytest.mark.asyncio
async def test_ceremony_step_executed_payload_status_enum() -> None:
    """Test that status field only contains valid enum values."""
    schema = _get_payload_schema("CeremonyStepExecutedPayload")
    
    # Verify schema has enum constraint
    assert "enum" in schema["properties"]["status"]
    valid_statuses = schema["properties"]["status"]["enum"]
    assert set(valid_statuses) == {"COMPLETED", "FAILED", "CANCELLED"}
    
    definition = create_test_definition()
    instance = create_test_instance(definition)
    
    # Test with COMPLETED status
    step_handler_port = AsyncMock(spec=StepHandlerPort)
    step_handler_port.execute_step.return_value = StepResult(
        status=StepStatus.COMPLETED,
        output={},
    )
    
    persistence_port = AsyncMock(spec=PersistencePort)
    
    published_events: list[dict[str, Any]] = []
    
    async def capture_publish(subject: str, envelope: Any) -> None:
        published_events.append({
            "subject": subject,
            "payload": envelope.payload,
        })
    
    messaging_port = AsyncMock(spec=MessagingPort)
    messaging_port.publish_event.side_effect = capture_publish
    
    runner = CeremonyRunner(
        step_handler_port=step_handler_port,
        messaging_port=messaging_port,
        persistence_port=persistence_port,
    )
    
    await runner.execute_step(instance, StepId("test_step"))
    
    step_executed_events = [
        event for event in published_events
        if event["subject"] == "ceremony.step.executed"
    ]
    
    assert len(step_executed_events) == 1
    payload = step_executed_events[0]["payload"]
    
    # Verify status is in enum
    assert payload["status"] in valid_statuses


def test_ceremony_step_executed_schema_required_fields() -> None:
    """Test that schema defines all required fields correctly."""
    schema = _get_payload_schema("CeremonyStepExecutedPayload")
    
    # Verify required fields
    assert "required" in schema
    required_fields = set(schema["required"])
    expected_required = {"instance_id", "step_id", "status", "current_state", "output"}
    assert required_fields == expected_required, f"Required fields mismatch: {required_fields} != {expected_required}"
    
    # Verify error_message is NOT required (optional field)
    assert "error_message" not in schema["required"]


def test_ceremony_transition_applied_schema_required_fields() -> None:
    """Test that schema defines all required fields correctly."""
    schema = _get_payload_schema("CeremonyTransitionAppliedPayload")
    
    # Verify required fields
    assert "required" in schema
    required_fields = set(schema["required"])
    expected_required = {"instance_id", "from_state", "to_state", "trigger"}
    assert required_fields == expected_required, f"Required fields mismatch: {required_fields} != {expected_required}"
