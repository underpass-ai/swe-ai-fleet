"""Environment configuration adapter - Infrastructure layer.

Concrete implementation that loads configuration from environment variables.
"""

import os

from core.context.domain.service_config import ServiceConfig
from core.context.ports.config_port import ConfigPort


class EnvironmentConfigAdapter:
    """Adapter that loads configuration from environment variables.

    Following Hexagonal Architecture:
    - Implements ConfigPort (application layer interface)
    - Lives in infrastructure layer (adapters)
    - Pure infrastructure concern (environment variables)
    """

    def load(self) -> ServiceConfig:
        """Load service configuration from environment variables.

        Environment variables:
            GRPC_PORT: gRPC server port (default: 50054)
            NEO4J_URI: Neo4j connection URI (default: bolt://neo4j:7687)
            NEO4J_USER: Neo4j username (default: neo4j)
            NEO4J_PASSWORD: Neo4j password (required, no default)
            REDIS_HOST: Redis host (default: redis)
            REDIS_PORT: Redis port (default: 6379)
            NATS_URL: NATS server URL (default: nats://nats:4222)
            ENABLE_NATS: Enable NATS messaging (default: true, REQUIRED for Context Service)

        Returns:
            ServiceConfig: Validated configuration value object

        Raises:
            ValueError: If NEO4J_PASSWORD is not set or invalid port number

        Note:
            The Context Service will fail-fast at startup if ENABLE_NATS=false,
            as NATS is required for the service to function properly.
        """
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if not neo4j_password:
            raise ValueError("NEO4J_PASSWORD environment variable must be set")

        redis_port_str = os.getenv("REDIS_PORT", "6379")
        try:
            redis_port = int(redis_port_str)
        except ValueError as e:
            raise ValueError(f"REDIS_PORT must be a valid integer, got: {redis_port_str}") from e

        enable_nats_str = os.getenv("ENABLE_NATS", "true").lower()
        enable_nats = enable_nats_str in ("true", "1", "yes", "on")

        return ServiceConfig(
            grpc_port=os.getenv("GRPC_PORT", "50054"),
            neo4j_uri=os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
            neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
            neo4j_password=neo4j_password,
            redis_host=os.getenv("REDIS_HOST", "redis"),
            redis_port=redis_port,
            nats_url=os.getenv("NATS_URL", "nats://nats:4222"),
            enable_nats=enable_nats,
        )
