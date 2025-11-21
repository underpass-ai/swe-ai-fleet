"""Unit tests for HandleStoryPhaseTransitionUseCase."""

from unittest.mock import AsyncMock

import pytest
from core.context.application.usecases.handle_story_phase_transition import (
    HandleStoryPhaseTransitionUseCase,
)
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.phase_transition import PhaseTransition

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_execute_invalidates_cache():
    """Test that execute invalidates cache for the story."""
    # Arrange
    graph_command = AsyncMock()
    cache_service = AsyncMock()
    cache_service.scan = AsyncMock(return_value=(0, [b"key1", b"key2"]))
    cache_service.delete = AsyncMock(return_value=2)

    use_case = HandleStoryPhaseTransitionUseCase(
        graph_command=graph_command,
        cache_service=cache_service,
    )

    transition = PhaseTransition(
        story_id=StoryId("STORY-123"),
        from_phase="DISCOVERY",
        to_phase="PLANNING",
        timestamp="2025-11-10T19:00:00Z",
    )

    # Act
    await use_case.execute(transition)

    # Assert - cache should be called (scan + delete)
    assert cache_service.scan.called or cache_service.delete.called


@pytest.mark.asyncio
async def test_execute_records_transition():
    """Test that execute records the phase transition."""
    # Arrange
    graph_command = AsyncMock()
    cache_service = AsyncMock()
    cache_service.scan = AsyncMock(return_value=(0, []))

    use_case = HandleStoryPhaseTransitionUseCase(
        graph_command=graph_command,
        cache_service=cache_service,
    )

    transition = PhaseTransition(
        story_id=StoryId("STORY-456"),
        from_phase="PLANNING",
        to_phase="BUILD",
        timestamp="2025-11-10T19:00:00Z",
    )

    # Act
    await use_case.execute(transition)

    # Assert - should call graph_command to save transition
    graph_command.save_phase_transition.assert_called_once_with(transition)


@pytest.mark.asyncio
async def test_execute_handles_missing_cache():
    """Test execute when cache store is None."""
    # Arrange
    graph_command = AsyncMock()

    use_case = HandleStoryPhaseTransitionUseCase(
        graph_command=graph_command,
        cache_service=None,
    )

    transition = PhaseTransition(
        story_id=StoryId("STORY-789"),
        from_phase="BUILD",
        to_phase="VALIDATE",
        timestamp="2025-11-10T19:00:00Z",
    )

    # Act - should not raise error
    await use_case.execute(transition)

    # Assert
    graph_command.save_phase_transition.assert_called_once_with(transition)


@pytest.mark.asyncio
async def test_execute_with_different_phases():
    """Test execute with various phase transitions."""
    # Arrange
    graph_command = AsyncMock()
    cache_service = AsyncMock()
    cache_service.scan = AsyncMock(return_value=(0, []))

    use_case = HandleStoryPhaseTransitionUseCase(
        graph_command=graph_command,
        cache_service=cache_service,
    )

    transitions = [
        ("DISCOVERY", "PLANNING"),
        ("PLANNING", "BUILD"),
        ("BUILD", "VALIDATE"),
        ("VALIDATE", "DEPLOY"),
    ]

    for i, (from_phase, to_phase) in enumerate(transitions):
        transition = PhaseTransition(
            story_id=StoryId(f"STORY-{from_phase}"),
            from_phase=from_phase,
            to_phase=to_phase,
            timestamp=f"2025-11-10T19:{i:02d}:00Z",
        )

        # Act
        await use_case.execute(transition)

    # Assert
    assert graph_command.save_phase_transition.call_count == len(transitions)

