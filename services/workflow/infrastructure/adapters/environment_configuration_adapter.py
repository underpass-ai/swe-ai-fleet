"""Environment configuration adapter.

Implements ConfigurationPort using environment variables.
Following Hexagonal Architecture (Adapter).
"""

import os

from services.workflow.application.ports.configuration_port import ConfigurationPort


class EnvironmentConfigurationAdapter(ConfigurationPort):
    """Configuration adapter using environment variables.

    Reads configuration from os.environ.
    Fail-fast: Missing required config raises ValueError.

    Following Hexagonal Architecture:
    - This is an ADAPTER (infrastructure implementation)
    - Implements ConfigurationPort (application port)
    - Contains OS-specific logic (os.getenv)
    """

    def get_config_value(self, key: str, default: str | None = None) -> str:
        """Get configuration value from environment.

        Args:
            key: Environment variable name
            default: Default value if not found

        Returns:
            Configuration value

        Raises:
            ValueError: If key not found and no default (fail-fast)
        """
        value = os.getenv(key, default)

        if value is None:
            raise ValueError(
                f"Required configuration '{key}' not found in environment "
                f"and no default provided (fail-fast)"
            )

        return value

    def get_int(self, key: str, default: int | None = None) -> int:
        """Get configuration value as integer.

        Args:
            key: Environment variable name
            default: Default value if not found

        Returns:
            Configuration value as int

        Raises:
            ValueError: If not found or not parseable as int (fail-fast)
        """
        value_str = os.getenv(key)

        if value_str is None:
            if default is None:
                raise ValueError(
                    f"Required configuration '{key}' not found in environment (fail-fast)"
                )
            return default

        try:
            return int(value_str)
        except ValueError as e:
            raise ValueError(
                f"Configuration '{key}' value '{value_str}' is not a valid integer"
            ) from e

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get configuration value as boolean.

        Args:
            key: Environment variable name
            default: Default value if not found

        Returns:
            Configuration value as bool
        """
        value_str = os.getenv(key)

        if value_str is None:
            return default

        # Parse boolean (case-insensitive)
        return value_str.lower() in ("true", "1", "yes", "on")

    def is_required_present(self, key: str) -> bool:
        """Check if a required configuration key is present.

        Args:
            key: Environment variable name

        Returns:
            True if key exists and has non-empty value
        """
        value = os.getenv(key)
        return value is not None and value.strip() != ""

