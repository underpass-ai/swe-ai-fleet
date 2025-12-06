"""Service configuration value object - Domain layer.

Configuration is defined in domain but loaded/injected from infrastructure.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ServiceConfig:
    """Context service configuration.

    This is a pure domain value object. Infrastructure layer is responsible
    for loading these values from environment variables or config files.

    Note: NATS is required for the Context Service to function properly.
    The service will fail-fast at startup if enable_nats=False.
    """

    grpc_port: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    redis_host: str
    redis_port: int
    nats_url: str
    enable_nats: bool  # Must be True for Context Service to function

    def __post_init__(self) -> None:
        """Validate configuration."""
        if not self.grpc_port:
            raise ValueError("gRPC port cannot be empty")
        if not self.neo4j_uri:
            raise ValueError("Neo4j URI cannot be empty")
        if not self.neo4j_user:
            raise ValueError("Neo4j user cannot be empty")
        if not self.neo4j_password:
            raise ValueError("Neo4j password cannot be empty")
        if not self.redis_host:
            raise ValueError("Redis host cannot be empty")
        if self.redis_port <= 0 or self.redis_port > 65535:
            raise ValueError(f"Redis port must be between 1 and 65535, got {self.redis_port}")
        if not self.nats_url:
            raise ValueError("NATS URL cannot be empty")

    @property
    def redis_url(self) -> str:
        """Build Redis connection URL."""
        return f"redis://{self.redis_host}:{self.redis_port}/0"
