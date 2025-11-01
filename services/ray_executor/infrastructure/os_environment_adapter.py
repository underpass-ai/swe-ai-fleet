"""OS environment adapter implementation."""

import os

from services.ray_executor.domain.environment_port import EnvironmentPort


class OsEnvironmentAdapter(EnvironmentPort):
    """Adapter for OS environment variables.

    This adapter implements EnvironmentPort using os.getenv().

    Following Hexagonal Architecture:
    - Implements port (interface) defined in domain
    - Provides access to OS environment configuration
    """

    def get_config_value(self, key: str, default: str = "") -> str:
        """Get configuration value from OS environment.

        Implements EnvironmentPort.get_config_value()
        """
        return os.getenv(key, default)