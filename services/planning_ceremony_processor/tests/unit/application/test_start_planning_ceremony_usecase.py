"""Tests for StartPlanningCeremonyUseCase."""

from unittest.mock import AsyncMock

import pytest

from core.ceremony_engine.application.ports.messaging_port import MessagingPort
from core.ceremony_engine.application.ports.persistence_port import PersistencePort
from core.ceremony_engine.application.ports.step_handler_port import StepHandlerPort
from core.ceremony_engine.domain.entities.ceremony_definition import CeremonyDefinition
from core.ceremony_engine.domain.value_objects import (
    Guard,
    GuardName,
    GuardType,
    Inputs,
    Output,
    Role,
    RetryPolicy,
    State,
    Step,
    StepHandlerType,
    StepId,
    StepResult,
    StepStatus,
    Timeouts,
    Transition,
    TransitionTrigger,
)
from services.planning_ceremony_processor.application.dto.start_planning_ceremony_request_dto import (
    StartPlanningCeremonyRequestDTO,
)
from services.planning_ceremony_processor.application.ports.ceremony_definition_port import (
    CeremonyDefinitionPort,
)
from services.planning_ceremony_processor.application.usecases.start_planning_ceremony_usecase import (
    StartPlanningCeremonyUseCase,
)


def _build_definition() -> CeremonyDefinition:
    return CeremonyDefinition(
        version="1.0",
        name="planning_ceremony",
        description="Test definition",
        inputs=Inputs(required=("input_data",), optional=()),
        outputs={"result": Output(type="object", schema=None)},
        states=(
            State(id="STARTED", description="start", initial=True, terminal=False),
            State(id="COMPLETED", description="done", initial=False, terminal=True),
        ),
        transitions=(
            Transition(
                from_state="STARTED",
                to_state="COMPLETED",
                trigger=TransitionTrigger("complete"),
                guards=(GuardName("all_done"),),
                description="complete",
            ),
        ),
        steps=(
            Step(
                id=StepId("submit_architect"),
                state="STARTED",
                handler=StepHandlerType.DELIBERATION_STEP,
                config={"prompt": "test", "role": "ARCHITECT", "num_agents": 1},
            ),
        ),
        guards={
            GuardName("all_done"): Guard(
                name=GuardName("all_done"),
                type=GuardType.AUTOMATED,
                check="all_steps_completed",
            )
        },
        roles=(
            Role(
                id="SYSTEM",
                description="system",
                allowed_actions=("submit_architect", "complete"),
            ),
            Role(
                id="ARCHITECT",
                description="architect",
                allowed_actions=("submit_architect", "complete"),
            ),
        ),
        timeouts=Timeouts(step_default=10, step_max=60, ceremony_max=600),
        retry_policies={"default": RetryPolicy(max_attempts=1, backoff_seconds=0, exponential_backoff=False)},
    )


@pytest.mark.asyncio
async def test_start_planning_ceremony_happy_path() -> None:
    definition_port = AsyncMock(spec=CeremonyDefinitionPort)
    definition_port.load_definition.return_value = _build_definition()

    step_handler_port = AsyncMock(spec=StepHandlerPort)
    step_handler_port.execute_step.return_value = StepResult(
        status=StepStatus.COMPLETED, output={}
    )
    persistence_port = AsyncMock(spec=PersistencePort)
    messaging_port = AsyncMock(spec=MessagingPort)

    use_case = StartPlanningCeremonyUseCase(
        definition_port=definition_port,
        step_handler_port=step_handler_port,
        persistence_port=persistence_port,
        messaging_port=messaging_port,
    )

    dto = StartPlanningCeremonyRequestDTO(
        ceremony_id="cer-1",
        definition_name="planning_ceremony",
        story_id="story-1",
        correlation_id="corr-1",
        inputs={"input_data": "value"},
        step_ids=("submit_architect",),
        requested_by="product_owner",
    )

    instance = await use_case.execute(dto)

    assert instance.instance_id == "cer-1:story-1"
    assert instance.correlation_id == "corr-1"
    persistence_port.save_instance.assert_awaited()
    step_handler_port.execute_step.assert_awaited_once()


@pytest.mark.asyncio
async def test_start_planning_ceremony_rejects_missing_required_input() -> None:
    definition_port = AsyncMock(spec=CeremonyDefinitionPort)
    definition_port.load_definition.return_value = _build_definition()

    use_case = StartPlanningCeremonyUseCase(
        definition_port=definition_port,
        step_handler_port=AsyncMock(spec=StepHandlerPort),
        persistence_port=AsyncMock(spec=PersistencePort),
        messaging_port=AsyncMock(spec=MessagingPort),
    )

    dto = StartPlanningCeremonyRequestDTO(
        ceremony_id="cer-1",
        definition_name="planning_ceremony",
        story_id="story-1",
        correlation_id="corr-1",
        inputs={},
        step_ids=("submit_architect",),
        requested_by="product_owner",
    )

    with pytest.raises(ValueError, match="Missing required inputs"):
        await use_case.execute(dto)


@pytest.mark.asyncio
async def test_start_planning_ceremony_rejects_unknown_step_id() -> None:
    definition_port = AsyncMock(spec=CeremonyDefinitionPort)
    definition_port.load_definition.return_value = _build_definition()

    use_case = StartPlanningCeremonyUseCase(
        definition_port=definition_port,
        step_handler_port=AsyncMock(spec=StepHandlerPort),
        persistence_port=AsyncMock(spec=PersistencePort),
        messaging_port=AsyncMock(spec=MessagingPort),
    )

    dto = StartPlanningCeremonyRequestDTO(
        ceremony_id="cer-1",
        definition_name="planning_ceremony",
        story_id="story-1",
        correlation_id="corr-1",
        inputs={"input_data": "value"},
        step_ids=("unknown_step",),
        requested_by="product_owner",
    )

    with pytest.raises(ValueError, match="Unknown step_ids"):
        await use_case.execute(dto)


def test_start_planning_ceremony_requires_ports() -> None:
    with pytest.raises(ValueError, match="definition_port is required"):
        StartPlanningCeremonyUseCase(
            definition_port=None,  # type: ignore[arg-type]
            step_handler_port=AsyncMock(spec=StepHandlerPort),
            persistence_port=AsyncMock(spec=PersistencePort),
            messaging_port=AsyncMock(spec=MessagingPort),
        )


def test_start_planning_ceremony_requires_step_handler_port() -> None:
    with pytest.raises(ValueError, match="step_handler_port is required"):
        StartPlanningCeremonyUseCase(
            definition_port=AsyncMock(spec=CeremonyDefinitionPort),
            step_handler_port=None,  # type: ignore[arg-type]
            persistence_port=AsyncMock(spec=PersistencePort),
            messaging_port=AsyncMock(spec=MessagingPort),
        )


def test_start_planning_ceremony_requires_persistence_port() -> None:
    with pytest.raises(ValueError, match="persistence_port is required"):
        StartPlanningCeremonyUseCase(
            definition_port=AsyncMock(spec=CeremonyDefinitionPort),
            step_handler_port=AsyncMock(spec=StepHandlerPort),
            persistence_port=None,  # type: ignore[arg-type]
            messaging_port=AsyncMock(spec=MessagingPort),
        )


def test_start_planning_ceremony_requires_messaging_port() -> None:
    with pytest.raises(ValueError, match="messaging_port is required"):
        StartPlanningCeremonyUseCase(
            definition_port=AsyncMock(spec=CeremonyDefinitionPort),
            step_handler_port=AsyncMock(spec=StepHandlerPort),
            persistence_port=AsyncMock(spec=PersistencePort),
            messaging_port=None,  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_start_planning_ceremony_rejects_no_initial_state() -> None:
    """_get_initial_state_id raises when no state has initial=True (mock def bypasses domain validation)."""
    from types import SimpleNamespace

    mock_state = SimpleNamespace(id="A", initial=False)
    mock_step = SimpleNamespace(id=StepId("s1"))
    no_initial = SimpleNamespace(
        inputs=SimpleNamespace(required=()),
        states=[mock_state],
        steps=[mock_step],
    )
    definition_port = AsyncMock(spec=CeremonyDefinitionPort)
    definition_port.load_definition.return_value = no_initial

    use_case = StartPlanningCeremonyUseCase(
        definition_port=definition_port,
        step_handler_port=AsyncMock(spec=StepHandlerPort),
        persistence_port=AsyncMock(spec=PersistencePort),
        messaging_port=AsyncMock(spec=MessagingPort),
    )

    dto = StartPlanningCeremonyRequestDTO(
        ceremony_id="cer-1",
        definition_name="bad",
        story_id="story-1",
        correlation_id=None,
        inputs={},
        step_ids=("s1",),
        requested_by="user",
    )

    with pytest.raises(ValueError, match="No initial state found"):
        await use_case.execute(dto)


@pytest.mark.asyncio
async def test_start_planning_ceremony_uses_default_correlation_id() -> None:
    definition_port = AsyncMock(spec=CeremonyDefinitionPort)
    definition_port.load_definition.return_value = _build_definition()

    step_handler_port = AsyncMock(spec=StepHandlerPort)
    step_handler_port.execute_step.return_value = StepResult(
        status=StepStatus.COMPLETED, output={}
    )
    persistence_port = AsyncMock(spec=PersistencePort)
    messaging_port = AsyncMock(spec=MessagingPort)

    use_case = StartPlanningCeremonyUseCase(
        definition_port=definition_port,
        step_handler_port=step_handler_port,
        persistence_port=persistence_port,
        messaging_port=messaging_port,
    )

    dto = StartPlanningCeremonyRequestDTO(
        ceremony_id="cer-1",
        definition_name="planning_ceremony",
        story_id="story-1",
        correlation_id=None,
        inputs={"input_data": "value"},
        step_ids=("submit_architect",),
        requested_by="product_owner",
    )

    instance = await use_case.execute(dto)
    assert instance.correlation_id == "cer-1:story-1"
