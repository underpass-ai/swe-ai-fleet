# core/context/domain/story.py
from __future__ import annotations

from dataclasses import dataclass

from .entity_ids.story_id import StoryId


@dataclass(frozen=True)
class Story:
    """Domain model representing a Story entity in the context graph.

    A Story represents a user story that needs to be completed.
    It serves as the root entity in the context graph, connecting to plans, tasks, and decisions.

    Formerly known as Case (renamed for consistency with Planning Service).

    This is a pure domain entity with NO serialization methods.
    Use StoryMapper in infrastructure layer for conversions.
    """

    story_id: StoryId
    name: str

