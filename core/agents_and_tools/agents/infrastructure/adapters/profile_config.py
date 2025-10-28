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
        # up to agents_and_tools/
        current_file = Path(__file__)
        # __file__: core/agents_and_tools/agents/infrastructure/adapters/profile_config.py
        # Up 3 levels: core/agents_and_tools/
        agents_and_tools_root = current_file.parent.parent.parent.parent.parent
        profiles_path = agents_and_tools_root / "agents_and_tools" / "resources" / "profiles"

        if not profiles_path.exists():
            raise FileNotFoundError(
                f"Profiles directory does not exist: {profiles_path}. "
                "Configuration error: profiles must be available."
            )

        return str(profiles_path)

