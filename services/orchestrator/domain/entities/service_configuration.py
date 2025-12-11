"""Service configuration entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ServiceConfiguration:
    """Entity representing service configuration.
    
    Encapsulates all configuration needed to run the orchestrator service.
    Uses generic names that don't reveal infrastructure technology choices.
    
    Attributes:
        grpc_port: Port for the gRPC server
        messaging_url: URL for the messaging system
        messaging_enabled: Whether messaging is enabled
        executor_address: Address of the remote executor service
    """
    
    grpc_port: str
    messaging_url: str
    messaging_enabled: bool
    executor_address: str
    
    @property
    def is_messaging_enabled(self) -> bool:
        """Check if messaging is enabled."""
        return self.messaging_enabled
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "grpc_port": self.grpc_port,
            "messaging_url": self.messaging_url,
            "messaging_enabled": self.messaging_enabled,
            "executor_address": self.executor_address,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ServiceConfiguration:
        """Create from dictionary."""
        return cls(
            grpc_port=data["grpc_port"],
            messaging_url=data["messaging_url"],
            messaging_enabled=data["messaging_enabled"],
            executor_address=data["executor_address"],
        )
    
    @classmethod
    def create_default(cls) -> ServiceConfiguration:
        """Create default configuration.
        
        Returns:
            ServiceConfiguration with default values
        """
        return cls(
            grpc_port="50055",
            messaging_url="nats://nats:4222",
            messaging_enabled=True,
            executor_address="ray-executor:50056",
        )

