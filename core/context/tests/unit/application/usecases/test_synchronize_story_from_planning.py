"""Unit tests for SynchronizeStoryFromPlanningUseCase."""

from unittest.mock import Mock

import pytest

from core.context.application.usecases.synchronize_story_from_planning import (
    SynchronizeStoryFromPlanningUseCase,
)
from core.context.domain.entity_ids.epic_id import EpicId
from core.context.domain.entity_ids.story_id import StoryId
from core.context.domain.story import Story

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_execute_calls_save_story() -> None:
    """Execute calls graph.save_story with story entity."""
    graph_command = Mock()
    use_case = SynchronizeStoryFromPlanningUseCase(graph_command=graph_command)
    story = Story(
        story_id=StoryId("s-1"),
        epic_id=EpicId("E-1"),
        name="As a user I want to login",
    )

    await use_case.execute(story)

    graph_command.save_story.assert_called_once_with(story)
