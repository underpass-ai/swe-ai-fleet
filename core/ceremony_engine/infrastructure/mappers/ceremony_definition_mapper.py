"""Mapper for loading CeremonyDefinition from YAML.

Following Hexagonal Architecture:
- Mappers live in infrastructure layer
- Load definitions from YAML files
- NO business logic - pure data transformation
"""

from pathlib import Path

from core.ceremony_engine.domain.entities.ceremony_definition import CeremonyDefinition
from core.ceremony_engine.infrastructure.yaml_validator import (
    CeremonyDefinitionValidator,
)


class CeremonyDefinitionMapper:
    """
    Mapper for loading CeremonyDefinition from YAML.

    Responsibilities:
    - Load CeremonyDefinition from YAML file by name
    - Cache loaded definitions (optional optimization)

    NO business logic - pure data loading.
    """

    @staticmethod
    def load_by_name(definition_name: str, ceremonies_dir: str | Path = "config/ceremonies") -> CeremonyDefinition:
        """Load CeremonyDefinition from YAML file by name.

        Args:
            definition_name: Name of ceremony (e.g., "dummy_ceremony")
            ceremonies_dir: Directory containing ceremony YAML files

        Returns:
            CeremonyDefinition loaded from YAML

        Raises:
            FileNotFoundError: If ceremony file not found
            ValueError: If ceremony definition is invalid
        """
        ceremonies_path = Path(ceremonies_dir)
        yaml_file = ceremonies_path / f"{definition_name}.yaml"

        return CeremonyDefinitionValidator.validate_and_parse_from_file(yaml_file)
