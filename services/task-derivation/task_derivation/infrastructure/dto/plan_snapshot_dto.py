"""Infrastructure DTO for Planning Service plan snapshots."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanSnapshotDTO:
    """Raw snapshot returned by Planning Service adapters."""

    plan_id: str
    story_id: str
    title: str
    description: str
    acceptance_criteria: tuple[str, ...]
    technical_notes: str
    roles: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate payload using fail-fast strategy."""
        for attribute_name in ("plan_id", "story_id", "title", "description"):
            value = getattr(self, attribute_name)
            if not value or not value.strip():
                raise ValueError(f"{attribute_name} cannot be empty")

        if not self.acceptance_criteria:
            raise ValueError("acceptance_criteria cannot be empty")

        for criterion in self.acceptance_criteria:
            if not criterion or not criterion.strip():
                raise ValueError("acceptance_criteria entries cannot be empty")

        if not self.roles:
            raise ValueError("roles cannot be empty")

        for role in self.roles:
            if not role or not role.strip():
                raise ValueError("roles entries cannot be empty")

        if not self.technical_notes or not self.technical_notes.strip():
            raise ValueError("technical_notes cannot be empty")

