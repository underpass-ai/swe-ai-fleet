"""Load agent profiles with role-specific model configurations."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    yaml = None

logger = logging.getLogger(__name__)


@dataclass
class AgentProfile:
    """Agent profile with model configuration."""

    name: str
    model: str
    context_window: int
    temperature: float
    max_tokens: int

    @classmethod
    def from_yaml(cls, yaml_path: str | Path) -> "AgentProfile":
        """Load profile from YAML file."""
        if not YAML_AVAILABLE:
            raise ImportError("pyyaml required. Install with: pip install pyyaml")

        path = Path(yaml_path)
        if not path.exists():
            raise FileNotFoundError(f"Profile not found: {yaml_path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        return cls(
            name=data["name"],
            model=data["model"],
            context_window=data.get("context_window", 32768),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 4096),
        )




def get_profile_for_role(role: str, profiles_url: str) -> dict[str, Any]:
    """
    Get agent profile configuration for a role.

    Loads profile from YAML files in the specified directory.

    Args:
        role: Agent role (DEV, QA, ARCHITECT, DEVOPS, DATA)
        profiles_url: Path to directory containing profile YAML files (REQUIRED, must be str)

    Returns:
        Dictionary with model, temperature, max_tokens, context_window

    Raises:
        ValueError: If profiles_url is None or not provided
        FileNotFoundError: If profiles directory doesn't exist or profile not found
    """
    if profiles_url is None:
        raise ValueError("profiles_url is required. Configuration error: profiles directory must be specified.")

    role = role.upper()
    profiles_dir = Path(profiles_url)

    # Fail fast if directory doesn't exist
    if not profiles_dir.exists():
        raise FileNotFoundError(f"Profiles directory does not exist: {profiles_dir}")

    if profiles_dir.exists() and YAML_AVAILABLE:
        # Load role-to-filename mapping from roles.yaml
        roles_config_path = profiles_dir / "roles.yaml"
        with open(roles_config_path) as f:
            roles_config = yaml.safe_load(f)
        role_to_file = roles_config.get("role_files", {})

        profile_file = profiles_dir / role_to_file.get(role, f"{role.lower()}.yaml")

        if profile_file.exists():
            try:
                profile = AgentProfile.from_yaml(profile_file)
                logger.info(f"Loaded profile for {role} from {profile_file}")
                return {
                    "model": profile.model,
                    "temperature": profile.temperature,
                    "max_tokens": profile.max_tokens,
                    "context_window": profile.context_window,
                }
            except Exception as e:
                # Fail fast: log error and fall through to generic defaults
                logger.error(f"Failed to load profile from {profile_file}: {e}")
                # Re-raise to fail fast
                raise

    # Fail fast: no profile found or YAML unavailable
    raise FileNotFoundError(f"No profile found for role {role}. Either profiles directory doesn't exist or roles.yaml is missing.")

