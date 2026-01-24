"""Unit tests for RehydrationUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from core.ceremony_engine.application.ports.definition_port import DefinitionPort
from core.ceremony_engine.application.ports.rehydration_port import RehydrationPort
from core.ceremony_engine.application.use_cases.rehydration_usecase import RehydrationUseCase
from core.ceremony_engine.domain.entities.ceremony_definition import CeremonyDefinition
from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance
from core.ceremony_engine.domain.value_objects import (
    Inputs,
    Output,
    RetryPolicy,
    Role,
    State,
    Step,
    StepHandlerType,
    StepId,
    StepStatusMap,
    Timeouts,
    Transition,
    TransitionTrigger,
)


def _definition(name: str = "test_ceremony") -> CeremonyDefinition:
    return CeremonyDefinition(
        version="1.0",
        name=name,
        description="Test ceremony",
        inputs=Inputs(required=(), optional=()),
        outputs={"result": Output(type="object", schema=None)},
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
                id=StepId("process_step"),
                state="STARTED",
                handler=StepHandlerType.AGGREGATION_STEP,
                config={"operation": "test"},
            ),
        ),
        guards={},
        roles=(Role(id="SYSTEM", description="System", allowed_actions=()),),
        timeouts=Timeouts(step_default=60, step_max=3600, ceremony_max=86400),
        retry_policies={"default": RetryPolicy(max_attempts=1, backoff_seconds=0, exponential_backoff=False)},
    )


def _instance(definition: CeremonyDefinition) -> CeremonyInstance:
    now = datetime.now(UTC)
    return CeremonyInstance(
        instance_id="instance-1",
        definition=definition,
        current_state="STARTED",
        step_status=StepStatusMap(entries=()),
        correlation_id="corr-1",
        idempotency_keys=frozenset(),
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_rehydrate_instance_happy_path() -> None:
    definition = _definition()
    instance = _instance(definition)
    rehydration_port = AsyncMock(spec=RehydrationPort)
    rehydration_port.rehydrate_instance.return_value = instance
    definition_port = AsyncMock(spec=DefinitionPort)
    definition_port.load_definition.return_value = definition

    use_case = RehydrationUseCase(
        rehydration_port=rehydration_port, definition_port=definition_port
    )

    result = await use_case.rehydrate_instance("instance-1")

    assert result == instance


@pytest.mark.asyncio
async def test_rehydrate_instance_rejects_invalid_definition() -> None:
    definition = _definition()
    instance = _instance(definition)
    rehydration_port = AsyncMock(spec=RehydrationPort)
    rehydration_port.rehydrate_instance.return_value = instance
    definition_port = AsyncMock(spec=DefinitionPort)
    changed = _definition()
    changed = changed.with_steps(
        (
            Step(
                id=StepId("other_step"),
                state="STARTED",
                handler=StepHandlerType.AGGREGATION_STEP,
                config={"operation": "test"},
            ),
        )
    )
    definition_port.load_definition.return_value = changed

    use_case = RehydrationUseCase(
        rehydration_port=rehydration_port, definition_port=definition_port
    )

    with pytest.raises(ValueError, match="does not match current definition"):
        await use_case.rehydrate_instance("instance-1")


@pytest.mark.asyncio
async def test_rehydrate_instances_by_correlation_id() -> None:
    definition = _definition()
    instance = _instance(definition)
    rehydration_port = AsyncMock(spec=RehydrationPort)
    rehydration_port.rehydrate_instances_by_correlation_id.return_value = [instance]
    definition_port = AsyncMock(spec=DefinitionPort)
    definition_port.load_definition.return_value = definition

    use_case = RehydrationUseCase(
        rehydration_port=rehydration_port, definition_port=definition_port
    )

    result = await use_case.rehydrate_instances_by_correlation_id("corr-1")

    assert result == [instance]


def test_rehydration_usecase_requires_ports() -> None:
    with pytest.raises(ValueError, match="rehydration_port is required"):
        RehydrationUseCase(None, AsyncMock(spec=DefinitionPort))  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_rehydration_usecase_rejects_empty_ids() -> None:
    use_case = RehydrationUseCase(
        rehydration_port=AsyncMock(spec=RehydrationPort),
        definition_port=AsyncMock(spec=DefinitionPort),
    )

    with pytest.raises(ValueError, match="instance_id cannot be empty"):
        await use_case.rehydrate_instance(" ")

    with pytest.raises(ValueError, match="correlation_id cannot be empty"):
        await use_case.rehydrate_instances_by_correlation_id(" ")
