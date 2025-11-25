"""Port definition for Context Service integration."""

from __future__ import annotations

from typing import Protocol

from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)
from task_derivation.domain.value_objects.task_derivation.context.derivation_phase import (
    DerivationPhase,
)


class ContextPort(Protocol):
    """Provides rehydrated story context for prompt generation."""

    async def get_context(
        self,
        story_id: StoryId,
        role: ContextRole,
        phase: DerivationPhase = DerivationPhase.PLAN,
    ) -> str:
        """Return formatted context blocks for the given story and role."""
        ...

