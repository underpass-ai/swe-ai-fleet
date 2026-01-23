"""Unit tests for CeremonyInstanceMapper."""

from datetime import datetime, UTC

from core.ceremony_engine.domain.entities.ceremony_definition import CeremonyDefinition
from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance
from core.ceremony_engine.domain.value_objects import (
    Inputs,
    State,
    Step,
    StepHandlerType,
    StepId,
    StepOutputEntry,
    StepOutputMap,
    StepStatus,
    StepStatusEntry,
    StepStatusMap,
    Timeouts,
    Transition,
    TransitionTrigger,
)
from core.ceremony_engine.infrastructure.mappers.ceremony_instance_mapper import (
    CeremonyInstanceMapper,
)


def _definition() -> CeremonyDefinition:
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
            id=StepId("process_step"),
            state="STARTED",
            handler=StepHandlerType.AGGREGATION_STEP,
            config={"operation": "test"},
        ),
    )
    return CeremonyDefinition(
        version="1.0",
        name="test_ceremony",
        description="Test ceremony",
        inputs=Inputs(required=(), optional=()),
        outputs={},
        states=states,
        transitions=transitions,
        steps=steps,
        guards={},
        roles=(),
        timeouts=Timeouts(step_default=300, step_max=600, ceremony_max=3600),
        retry_policies={},
    )


def _instance(definition: CeremonyDefinition) -> CeremonyInstance:
    now = datetime.now(UTC)
    return CeremonyInstance(
        instance_id="instance-1",
        definition=definition,
        current_state="STARTED",
        step_status=StepStatusMap(
            entries=(StepStatusEntry(step_id=StepId("process_step"), status=StepStatus.COMPLETED),)
        ),
        step_outputs=StepOutputMap(
            entries=(StepOutputEntry(step_id=StepId("process_step"), output={"value": 1}),)
        ),
        correlation_id="corr-1",
        idempotency_keys=frozenset({"key-1", "key-2"}),
        created_at=now,
        updated_at=now,
    )


def test_to_neo4j_dict() -> None:
    definition = _definition()
    instance = _instance(definition)

    data = CeremonyInstanceMapper.to_neo4j_dict(instance)

    assert data["instance_id"] == "instance-1"
    assert data["definition_name"] == "test_ceremony"
    assert data["current_state"] == "STARTED"
    assert "step_status_json" in data
    assert "idempotency_keys_json" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_from_neo4j_dict_round_trip() -> None:
    definition = _definition()
    instance = _instance(definition)
    data = CeremonyInstanceMapper.to_neo4j_dict(instance)

    restored = CeremonyInstanceMapper.from_neo4j_dict(data, definition)

    assert restored.instance_id == instance.instance_id
    assert restored.definition.name == instance.definition.name
    assert restored.current_state == instance.current_state
    assert restored.step_status == instance.step_status
    assert restored.step_outputs == instance.step_outputs
    assert restored.correlation_id == instance.correlation_id
    assert restored.idempotency_keys == instance.idempotency_keys


def test_to_valkey_json_and_from_valkey_json() -> None:
    definition = _definition()
    instance = _instance(definition)

    json_str = CeremonyInstanceMapper.to_valkey_json(instance)
    restored = CeremonyInstanceMapper.from_valkey_json(json_str, definition)

    assert restored.instance_id == instance.instance_id
    assert restored.definition.name == instance.definition.name
    assert restored.current_state == instance.current_state
    assert restored.step_status == instance.step_status
    assert restored.step_outputs == instance.step_outputs
    assert restored.correlation_id == instance.correlation_id
    assert restored.idempotency_keys == instance.idempotency_keys
