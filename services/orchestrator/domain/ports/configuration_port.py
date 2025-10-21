"""Port (interface) for configuration access."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.orchestrator.domain.entities import ServiceConfiguration


class ConfigurationPort(ABC):
    """Port defining the interface for configuration access.
    
    This port abstracts how configuration is loaded (environment variables,
    config files, etc.), allowing the domain to remain independent of
    configuration sources.
    
    Following Hexagonal Architecture:
    - Domain defines the port (this interface)
    - Infrastructure provides the adapter (e.g., EnvironmentConfigurationAdapter)
    """
    
    @abstractmethod
    def get_service_configuration(self) -> ServiceConfiguration:
        """Get service configuration.
        
        Returns:
            ServiceConfiguration entity with all service settings
        """
        pass
    
    @abstractmethod
    def get_config_value(self, key: str, default: str = "") -> str:
        """Get a specific configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        pass

