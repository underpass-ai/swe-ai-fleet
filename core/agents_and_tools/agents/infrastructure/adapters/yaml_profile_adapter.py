"""Adapter for loading profiles from YAML files."""

import yaml
from pathlib import Path

from core.agents_and_tools.agents.domain.entities.agent_profile import AgentProfile
from core.agents_and_tools.agents.infrastructure.dtos.agent_profile_dto import AgentProfileDTO
from core.agents_and_tools.agents.infrastructure.mappers.agent_profile_mapper import AgentProfileMapper


def load_profile_from_yaml(
    yaml_path: str,
    mapper: AgentProfileMapper,
) -> AgentProfile:
    """Load AgentProfile from YAML file (fail fast).

    Args:
        yaml_path: Path to YAML file
        mapper: Mapper instance to convert DTO to Entity (injected dependency)

    Returns:
        AgentProfile domain entity

    Raises:
        FileNotFoundError: If file doesn't exist
        KeyError: If required fields missing in YAML
    """

    path = Path(yaml_path)
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {yaml_path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    # Create DTO from YAML data (fail fast if fields missing)
    dto = AgentProfileDTO(
        name=data["name"],
        model=data["model"],
        context_window=data["context_window"],
        temperature=data["temperature"],
        max_tokens=data["max_tokens"],
    )

    # Convert DTO to Entity using injected mapper
    return mapper.dto_to_entity(dto)

