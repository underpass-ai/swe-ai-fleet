"""Load agent profiles with role-specific model configurations."""

from pathlib import Path

from core.agents_and_tools.agents.infrastructure.adapters.yaml_profile_adapter import YamlProfileLoaderAdapter


def _get_default_profiles_url():
    """Get default profiles directory URL.
    
    Returns:
        Path to default profiles directory
    """
    # Go from core/agents_and_tools/agents/profile_loader.py up to project root
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent  # up to core/
    profiles_path = project_root / "agents_and_tools" / "resources" / "profiles"
    return str(profiles_path)


def get_profile_for_role(role: str, profiles_url: str | None = None):
    """
    Get agent profile configuration for a role.

    Delegates to infrastructure adapter to load from YAML files.

    Args:
        role: Agent role (DEV, QA, ARCHITECT, DEVOPS, DATA)
        profiles_url: Path to directory containing profile YAML files (optional, uses default if not provided)

    Returns:
        AgentProfile domain entity

    Raises:
        ValueError: If profiles_url is None or not provided
        FileNotFoundError: If profiles directory doesn't exist or profile not found
    """
    if profiles_url is None:
        profiles_url = _get_default_profiles_url()
    
    adapter = YamlProfileLoaderAdapter(profiles_url)
    return adapter.load_profile_for_role(role)

