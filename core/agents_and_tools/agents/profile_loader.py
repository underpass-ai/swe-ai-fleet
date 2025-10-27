"""Load agent profiles with role-specific model configurations."""

from core.agents_and_tools.agents.infrastructure.adapters.yaml_profile_adapter import YamlProfileLoaderAdapter


def get_profile_for_role(role: str, profiles_url: str):
    """
    Get agent profile configuration for a role.

    Delegates to infrastructure adapter to load from YAML files.

    Args:
        role: Agent role (DEV, QA, ARCHITECT, DEVOPS, DATA)
        profiles_url: Path to directory containing profile YAML files (REQUIRED, must be str)

    Returns:
        AgentProfile domain entity

    Raises:
        ValueError: If profiles_url is None or not provided
        FileNotFoundError: If profiles directory doesn't exist or profile not found
    """
    adapter = YamlProfileLoaderAdapter(profiles_url)
    return adapter.load_profile_for_role(role)

