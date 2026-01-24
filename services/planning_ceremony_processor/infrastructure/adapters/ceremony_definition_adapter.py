"""Adapter for loading ceremony definitions from YAML."""

from dataclasses import dataclass

from core.ceremony_engine.domain.entities.ceremony_definition import CeremonyDefinition
from core.ceremony_engine.infrastructure.mappers.ceremony_definition_mapper import (
    CeremonyDefinitionMapper,
)
from services.planning_ceremony_processor.application.ports.ceremony_definition_port import (
    CeremonyDefinitionPort,
)


@dataclass
class CeremonyDefinitionAdapter(CeremonyDefinitionPort):
    """Load ceremony definitions using core mapper."""

    ceremonies_dir: str

    def __post_init__(self) -> None:
        if not self.ceremonies_dir or not self.ceremonies_dir.strip():
            raise ValueError("ceremonies_dir cannot be empty")

    async def load_definition(self, name: str) -> CeremonyDefinition:
        if not name or not name.strip():
            raise ValueError("definition name cannot be empty")
        return CeremonyDefinitionMapper.load_by_name(name, self.ceremonies_dir)
