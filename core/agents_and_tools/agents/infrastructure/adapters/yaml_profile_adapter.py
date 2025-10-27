"""Adapter for loading profiles from YAML files."""

import yaml
from pathlib import Path

from core.agents_and_tools.agents.domain.entities.agent_profile import AgentProfile
from core.agents_and_tools.agents.domain.ports.profile_loader_port import ProfileLoaderPort
from core.agents_and_tools.agents.infrastructure.dtos.agent_profile_dto import AgentProfileDTO
from core.agents_and_tools.agents.infrastructure.mappers.agent_profile_mapper import AgentProfileMapper


class YamlProfileLoaderAdapter(ProfileLoaderPort):
    """Adapter for loading agent profiles from YAML files."""

    def __init__(self, profiles_url: str):
        """Initialize adapter with profiles directory.

        Args:
            profiles_url: Path to directory containing profile YAML files
        """
        if profiles_url is None:
            raise ValueError("profiles_url is required. Configuration error: profiles directory must be specified.")

        self.profiles_url = profiles_url
        self.profiles_dir = Path(profiles_url)

        # Fail fast if directory doesn't exist
        if not self.profiles_dir.exists():
            raise FileNotFoundError(f"Profiles directory does not exist: {self.profiles_dir}")

    def load_profile_for_role(self, role: str) -> AgentProfile:
        """Load AgentProfile for a specific role (fail fast).

        Args:
            role: Agent role (DEV, QA, ARCHITECT, DEVOPS, DATA)

        Returns:
            AgentProfile domain entity

        Raises:
            FileNotFoundError: If profile not found for the role
            KeyError: If required fields missing in YAML
        """
        role = role.upper()

        # Load role-to-filename mapping from roles.yaml
        roles_config_path = self.profiles_dir / "roles.yaml"
        with open(roles_config_path) as f:
            roles_config = yaml.safe_load(f)
        role_to_file = roles_config.get("role_files", {})

        profile_file = self.profiles_dir / role_to_file.get(role, f"{role.lower()}.yaml")

        if not profile_file.exists():
            raise FileNotFoundError(f"No profile found for role {role}")

        # Load profile from YAML
        with open(profile_file) as f:
            data = yaml.safe_load(f)

        # Create DTO from YAML data (fail fast if fields missing)
        dto = AgentProfileDTO(
            name=data["name"],
            model=data["model"],
            context_window=data["context_window"],
            temperature=data["temperature"],
            max_tokens=data["max_tokens"],
        )

        # Convert DTO to Entity using mapper
        mapper = AgentProfileMapper()
        return mapper.dto_to_entity(dto)


def load_profile_for_role(
    role: str,
    profiles_url: str,
) -> AgentProfile:
    """Load AgentProfile for a specific role (fail fast).

    Args:
        role: Agent role (DEV, QA, ARCHITECT, DEVOPS, DATA)
        profiles_url: Path to directory containing profile YAML files (REQUIRED)

    Returns:
        AgentProfile domain entity

    Raises:
        ValueError: If profiles_url is None or not provided
        FileNotFoundError: If profiles directory doesn't exist or profile not found
        KeyError: If required fields missing in YAML
    """
    if profiles_url is None:
        raise ValueError("profiles_url is required. Configuration error: profiles directory must be specified.")

    role = role.upper()
    profiles_dir = Path(profiles_url)

    # Fail fast if directory doesn't exist
    if not profiles_dir.exists():
        raise FileNotFoundError(f"Profiles directory does not exist: {profiles_dir}")

    # Load role-to-filename mapping from roles.yaml
    roles_config_path = profiles_dir / "roles.yaml"
    with open(roles_config_path) as f:
        roles_config = yaml.safe_load(f)
    role_to_file = roles_config.get("role_files", {})

    profile_file = profiles_dir / role_to_file.get(role, f"{role.lower()}.yaml")

    if not profile_file.exists():
        raise FileNotFoundError(f"No profile found for role {role}")

    # Load profile from YAML
    with open(profile_file) as f:
        data = yaml.safe_load(f)

    # Create DTO from YAML data (fail fast if fields missing)
    dto = AgentProfileDTO(
        name=data["name"],
        model=data["model"],
        context_window=data["context_window"],
        temperature=data["temperature"],
        max_tokens=data["max_tokens"],
    )

    # Convert DTO to Entity using mapper
    mapper = AgentProfileMapper()
    return mapper.dto_to_entity(dto)

