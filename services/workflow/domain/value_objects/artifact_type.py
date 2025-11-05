"""Artifact type value object.

Maps workflow actions to artifact types for validation.
Following Domain-Driven Design principles.
"""

from core.agents_and_tools.agents.domain.entities.rbac.action import ActionEnum


class ArtifactType:
    """Domain logic for artifact type identification.

    Maps actions to the type of artifact being validated.
    This is domain knowledge, not infrastructure concern.
    """

    @staticmethod
    def from_action(action: ActionEnum | None) -> str:
        """Get artifact type for a workflow action.

        Domain knowledge: Which actions validate which artifacts.

        Args:
            action: Workflow action enum

        Returns:
            Artifact type identifier (design, tests, story, or empty)
        """
        if action is None:
            return ""

        # Domain mapping: Action → Artifact Type
        mapping = {
            ActionEnum.APPROVE_DESIGN: "design",
            ActionEnum.REJECT_DESIGN: "design",
            ActionEnum.APPROVE_TESTS: "tests",
            ActionEnum.REJECT_TESTS: "tests",
            ActionEnum.APPROVE_STORY: "story",
            ActionEnum.REJECT_STORY: "story",
        }

        return mapping.get(action, "")

