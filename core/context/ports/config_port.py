"""Configuration port - Application layer interface.

Defines the contract for loading service configuration.
Following Hexagonal Architecture: Port (interface) in application, Adapter in infrastructure.
"""

from typing import Protocol

from core.context.domain.service_config import ServiceConfig


class ConfigPort(Protocol):
    """Port for loading service configuration.

    This interface defines how the application layer accesses configuration.
    Concrete implementations (adapters) can load from environment variables,
    config files, cloud secrets, etc.
    """

    def load(self) -> ServiceConfig:
        """Load and return service configuration.

        Returns:
            ServiceConfig: Validated configuration value object

        Raises:
            ValueError: If required configuration is missing or invalid
        """
        ...
