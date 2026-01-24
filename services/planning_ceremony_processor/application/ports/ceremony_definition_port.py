"""Port for loading ceremony definitions."""

from typing import Protocol

from core.ceremony_engine.domain.entities.ceremony_definition import CeremonyDefinition


class CeremonyDefinitionPort(Protocol):
    """Port defining interface for loading ceremony definitions."""

    async def load_definition(self, name: str) -> CeremonyDefinition:
        """Load ceremony definition by name."""
        ...
