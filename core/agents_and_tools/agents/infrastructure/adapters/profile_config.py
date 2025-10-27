"""Configuration helper for agent profiles."""

from pathlib import Path


class ProfileConfig:
    """Configuration helper for loading agent profiles.

    Initially used as a helper to get default profiles directory.
    Can be extended for other configuration needs.
    """

    @staticmethod
    def get_default_profiles_url() -> str:
        """Get default profiles directory URL (fail-fast).

        Returns:
            Path to default profiles directory

        Raises:
            FileNotFoundError: If profiles directory doesn't exist
        """
        # Go from core/agents_and_tools/agents/infrastructure/adapters/profile_config.py
        # up to project root/core/
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent  # up to core/
        profiles_path = project_root / "agents_and_tools" / "resources" / "profiles"

        if not profiles_path.exists():
            raise FileNotFoundError(
                f"Profiles directory does not exist: {profiles_path}. "
                "Configuration error: profiles must be available."
            )

        return str(profiles_path)

