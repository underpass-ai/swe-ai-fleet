"""Environment-based configuration adapter."""
import logging
import os

from services.monitoring.domain.ports.configuration.configuration_port import ConfigurationPort

logger = logging.getLogger(__name__)


class EnvironmentConfigurationAdapter(ConfigurationPort):
    """Concrete adapter for reading configuration from environment variables."""
    
    def get_nats_url(self) -> str:
        """Get NATS server URL from environment.
        
        Returns:
            NATS URL string
        """
        return os.getenv(
            "NATS_URL",
            "nats://nats.swe-ai-fleet.svc.cluster.local:4222"
        )
    
    def get_orchestrator_address(self) -> str:
        """Get orchestrator service address from environment.
        
        Returns:
            Orchestrator address string
        """
        return os.getenv(
            "ORCHESTRATOR_ADDRESS",
            "orchestrator.swe-ai-fleet.svc.cluster.local:50055"
        )
    
    def get_port(self) -> int:
        """Get application port from environment.
        
        Returns:
            Port number
        """
        try:
            return int(os.getenv("PORT", "8080"))
        except ValueError:
            logger.warning("Invalid PORT env var, using default 8080")
            return 8080
    
    def get_config_value(self, key: str, default: str = None) -> str:
        """Get a configuration value from environment.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            Configuration value
        """
        return os.getenv(key, default)
