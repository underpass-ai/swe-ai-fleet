"""Environment configuration adapter."""

from __future__ import annotations

import os

from services.orchestrator.domain.entities import ServiceConfiguration
from services.orchestrator.domain.ports import ConfigurationPort


class EnvironmentConfigurationAdapter(ConfigurationPort):
    """Adapter implementing configuration access via environment variables.
    
    This adapter implements the ConfigurationPort interface using OS
    environment variables, keeping infrastructure concerns separated
    from domain logic.
    """
    
    def get_service_configuration(self) -> ServiceConfiguration:
        """Get service configuration from environment variables.
        
        Implements ConfigurationPort.get_service_configuration by reading
        from OS environment variables.
        
        Environment variables:
            GRPC_PORT: gRPC server port (default: 50055)
            NATS_URL: NATS messaging URL (default: nats://nats:4222)
            ENABLE_NATS: Enable NATS messaging (default: true)
            RAY_EXECUTOR_ADDRESS: Ray Executor address (default: ray-executor...)
            
        Returns:
            ServiceConfiguration entity
        """
        grpc_port = os.getenv("GRPC_PORT", "50055")
        messaging_url = os.getenv("NATS_URL", "nats://nats:4222")
        messaging_enabled = os.getenv("ENABLE_NATS", "true").lower() == "true"
        executor_address = os.getenv(
            "RAY_EXECUTOR_ADDRESS",
            "ray-executor.swe-ai-fleet.svc.cluster.local:50056"
        )
        
        return ServiceConfiguration(
            grpc_port=grpc_port,
            messaging_url=messaging_url,
            messaging_enabled=messaging_enabled,
            executor_address=executor_address,
        )
    
    def get_config_value(self, key: str, default: str = "") -> str:
        """Get a specific configuration value from environment.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            Configuration value
        """
        return os.getenv(key, default)

