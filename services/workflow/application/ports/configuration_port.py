"""Configuration port for accessing system configuration.

Defines interface for configuration access.
Following Hexagonal Architecture (Port).
"""

from typing import Protocol


class ConfigurationPort(Protocol):
    """Port for accessing configuration values.

    Abstracts configuration sources (environment variables, files, etc.).
    Implemented by infrastructure adapters.

    Following Hexagonal Architecture:
    - This is a PORT (interface)
    - Infrastructure provides ADAPTERS (EnvironmentAdapter, etc.)
    - Application depends on PORT, not concrete source
    """

    def get_config_value(self, key: str, default: str | None = None) -> str:
        """Get configuration value.

        Args:
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value

        Raises:
            ValueError: If key not found and no default provided (fail-fast)
        """
        ...

    def get_int(self, key: str, default: int | None = None) -> int:
        """Get configuration value as integer.

        Args:
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value as int

        Raises:
            ValueError: If key not found and no default, or if not parseable as int
        """
        ...

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get configuration value as boolean.

        Args:
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value as bool
        """
        ...

    def is_required_present(self, key: str) -> bool:
        """Check if a required configuration key is present.

        Args:
            key: Configuration key

        Returns:
            True if key exists and has non-empty value
        """
        ...

