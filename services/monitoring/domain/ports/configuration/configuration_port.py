"""Port for configuration management (technology-agnostic)."""
from abc import ABC, abstractmethod


class ConfigurationPort(ABC):
    """Abstract port for configuration operations."""
    
    @abstractmethod
    def get_nats_url(self) -> str:
        """Get NATS server URL.
        
        Returns:
            NATS URL string
        """
        pass
    
    @abstractmethod
    def get_port(self) -> int:
        """Get application port.
        
        Returns:
            Port number
        """
        pass
    
    @abstractmethod
    def get_orchestrator_address(self) -> str:
        """Get orchestrator service address.
        
        Returns:
            Orchestrator address string
        """
        pass
    
    @abstractmethod
    def get_config_value(self, key: str, default: str = None) -> str:
        """Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value
        """
        pass
