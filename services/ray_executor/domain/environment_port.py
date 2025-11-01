"""Port for environment configuration."""

from typing import Protocol


class EnvironmentPort(Protocol):
    """Port defining the interface for environment configuration access.

    This port abstracts environment variable access, allowing the domain
    to remain independent of OS/deployment details.

    Following Hexagonal Architecture (Dependency Inversion Principle):
    - Domain defines the port (this interface)
    - Infrastructure provides the adapter (OS environment implementation)
    """

    def get_config_value(self, key: str, default: str = "") -> str:
        """Get configuration value from environment.

        Args:
            key: Configuration key name
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        ...