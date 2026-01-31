"""Unit tests for AdvanceCeremonyOnAgentCompletedUseCase."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from core.ceremony_engine.application.ports.persistence_port import PersistencePort
from core.ceremony_engine.application.services.ceremony_runner import CeremonyRunner
from core.ceremony_engine.domain.value_objects.transition_trigger import (
    TransitionTrigger,
)
from services.planning_ceremony_processor.application.usecases.advance_ceremony_on_agent_completed_usecase import (
    AdvanceCeremonyOnAgentCompletedUseCase,
)


@pytest.fixture
def mock_persistence_port() -> MagicMock:
    return MagicMock(spec=PersistencePort)


@pytest.fixture
def mock_ceremony_runner() -> MagicMock:
    runner = MagicMock(spec=CeremonyRunner)
    runner.transition_state = AsyncMock(return_value=MagicMock(instance_id="i1"))
    return runner


@pytest.mark.asyncio
async def test_advance_rejects_empty_correlation_id(
    mock_persistence_port: MagicMock,
    mock_ceremony_runner: MagicMock,
) -> None:
    """advance raises ValueError when correlation_id is empty."""
    use_case = AdvanceCeremonyOnAgentCompletedUseCase(
        persistence_port=mock_persistence_port,
        ceremony_runner=mock_ceremony_runner,
    )
    with pytest.raises(ValueError, match="correlation_id cannot be empty"):
        await use_case.advance(
            correlation_id="",
            task_id="t1",
            payload={"trigger": "deliberation_done"},
        )
    mock_persistence_port.find_instances_by_correlation_id.assert_not_called()


@pytest.mark.asyncio
async def test_advance_rejects_whitespace_correlation_id(
    mock_persistence_port: MagicMock,
    mock_ceremony_runner: MagicMock,
) -> None:
    """advance raises ValueError when correlation_id is only whitespace."""
    use_case = AdvanceCeremonyOnAgentCompletedUseCase(
        persistence_port=mock_persistence_port,
        ceremony_runner=mock_ceremony_runner,
    )
    with pytest.raises(ValueError, match="correlation_id cannot be empty"):
        await use_case.advance(
            correlation_id="   ",
            task_id="t1",
            payload={"trigger": "deliberation_done"},
        )
    mock_persistence_port.find_instances_by_correlation_id.assert_not_called()


@pytest.mark.asyncio
async def test_advance_no_instances_returns_early(
    mock_persistence_port: MagicMock,
    mock_ceremony_runner: MagicMock,
) -> None:
    """advance does not call runner when no instances found."""
    mock_persistence_port.find_instances_by_correlation_id = AsyncMock(
        return_value=[]
    )
    use_case = AdvanceCeremonyOnAgentCompletedUseCase(
        persistence_port=mock_persistence_port,
        ceremony_runner=mock_ceremony_runner,
    )
    await use_case.advance(
        correlation_id="corr-1",
        task_id="task-1",
        payload={"trigger": "deliberation_done"},
    )
    mock_persistence_port.find_instances_by_correlation_id.assert_awaited_once_with(
        "corr-1"
    )
    mock_ceremony_runner.transition_state.assert_not_called()


@pytest.mark.asyncio
async def test_advance_no_trigger_in_payload_skips_runner(
    mock_persistence_port: MagicMock,
    mock_ceremony_runner: MagicMock,
) -> None:
    """advance does not call runner when payload has no trigger."""
    mock_instance = MagicMock(instance_id="i1")
    mock_persistence_port.find_instances_by_correlation_id = AsyncMock(
        return_value=[mock_instance]
    )
    use_case = AdvanceCeremonyOnAgentCompletedUseCase(
        persistence_port=mock_persistence_port,
        ceremony_runner=mock_ceremony_runner,
    )
    await use_case.advance(
        correlation_id="corr-1",
        task_id="task-1",
        payload={"task_id": "task-1"},
    )
    mock_ceremony_runner.transition_state.assert_not_called()


@pytest.mark.asyncio
async def test_advance_empty_trigger_in_payload_skips_runner(
    mock_persistence_port: MagicMock,
    mock_ceremony_runner: MagicMock,
) -> None:
    """advance does not call runner when payload trigger is empty string."""
    mock_instance = MagicMock(instance_id="i1")
    mock_persistence_port.find_instances_by_correlation_id = AsyncMock(
        return_value=[mock_instance]
    )
    use_case = AdvanceCeremonyOnAgentCompletedUseCase(
        persistence_port=mock_persistence_port,
        ceremony_runner=mock_ceremony_runner,
    )
    await use_case.advance(
        correlation_id="corr-1",
        task_id="task-1",
        payload={"trigger": ""},
    )
    mock_ceremony_runner.transition_state.assert_not_called()


@pytest.mark.asyncio
async def test_advance_with_trigger_calls_runner(
    mock_persistence_port: MagicMock,
    mock_ceremony_runner: MagicMock,
) -> None:
    """advance calls transition_state with instance and trigger when payload has trigger."""
    mock_instance = MagicMock(instance_id="i1")
    mock_persistence_port.find_instances_by_correlation_id = AsyncMock(
        return_value=[mock_instance]
    )
    use_case = AdvanceCeremonyOnAgentCompletedUseCase(
        persistence_port=mock_persistence_port,
        ceremony_runner=mock_ceremony_runner,
    )
    await use_case.advance(
        correlation_id="corr-1",
        task_id="task-1",
        payload={"trigger": "deliberation_done"},
    )
    mock_persistence_port.find_instances_by_correlation_id.assert_awaited_once_with(
        "corr-1"
    )
    mock_ceremony_runner.transition_state.assert_awaited_once()
    call_args = mock_ceremony_runner.transition_state.call_args
    assert call_args.args[0] is mock_instance
    assert call_args.args[1] == TransitionTrigger("deliberation_done")
    assert call_args.kwargs.get("context") is None


@pytest.mark.asyncio
async def test_advance_with_none_payload_skips_runner(
    mock_persistence_port: MagicMock,
    mock_ceremony_runner: MagicMock,
) -> None:
    """advance does not call runner when payload is None."""
    mock_instance = MagicMock(instance_id="i1")
    mock_persistence_port.find_instances_by_correlation_id = AsyncMock(
        return_value=[mock_instance]
    )
    use_case = AdvanceCeremonyOnAgentCompletedUseCase(
        persistence_port=mock_persistence_port,
        ceremony_runner=mock_ceremony_runner,
    )
    await use_case.advance(
        correlation_id="corr-1",
        task_id="task-1",
        payload=None,
    )
    mock_ceremony_runner.transition_state.assert_not_called()


def test_post_init_requires_persistence_port() -> None:
    """__post_init__ raises when persistence_port is None."""
    with pytest.raises(ValueError, match="persistence_port is required"):
        AdvanceCeremonyOnAgentCompletedUseCase(
            persistence_port=None,  # type: ignore[arg-type]
            ceremony_runner=MagicMock(spec=CeremonyRunner),
        )


def test_post_init_requires_ceremony_runner() -> None:
    """__post_init__ raises when ceremony_runner is None."""
    with pytest.raises(ValueError, match="ceremony_runner is required"):
        AdvanceCeremonyOnAgentCompletedUseCase(
            persistence_port=MagicMock(spec=PersistencePort),
            ceremony_runner=None,  # type: ignore[arg-type]
        )
