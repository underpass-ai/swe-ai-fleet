"""Environment configuration adapter for Planning Service."""

import logging
import os

from planning.application.ports.configuration_port import ConfigurationPort

logger = logging.getLogger(__name__)


class EnvironmentConfigurationAdapter(ConfigurationPort):
    """
    Adapter: Load configuration from environment variables.

    Infrastructure Layer Responsibility:
    - Read environment variables
    - Provide defaults
    - Fail fast if required config is missing

    Environment Variables:
    - NEO4J_URI: Neo4j connection URI (default: bolt://neo4j:7687)
    - NEO4J_USER: Neo4j username (default: neo4j)
    - NEO4J_PASSWORD: Neo4j password (required in production)
    - NEO4J_DATABASE: Neo4j database name (optional)
    - VALKEY_HOST: Valkey host (default: valkey)
    - VALKEY_PORT: Valkey port (default: 6379)
    - VALKEY_DB: Valkey database number (default: 0)
    - NATS_URL: NATS connection URL (default: nats://nats:4222)
    - GRPC_PORT: gRPC server port (default: 50054)
    """

    def get_neo4j_uri(self) -> str:
        """Get Neo4j connection URI."""
        return os.getenv("NEO4J_URI", "bolt://neo4j:7687")

    def get_neo4j_user(self) -> str:
        """Get Neo4j username."""
        return os.getenv("NEO4J_USER", "neo4j")

    def get_neo4j_password(self) -> str:
        """Get Neo4j password."""
        password = os.getenv("NEO4J_PASSWORD", "password")
        if password == "password":
            logger.warning("Using default Neo4j password - NOT for production!")
        return password

    def get_neo4j_database(self) -> str | None:
        """Get Neo4j database name (optional)."""
        return os.getenv("NEO4J_DATABASE")

    def get_valkey_host(self) -> str:
        """Get Valkey host."""
        return os.getenv("VALKEY_HOST", "valkey")

    def get_valkey_port(self) -> int:
        """Get Valkey port."""
        port_str = os.getenv("VALKEY_PORT", "6379")
        return int(port_str)

    def get_valkey_db(self) -> int:
        """Get Valkey database number."""
        db_str = os.getenv("VALKEY_DB", "0")
        return int(db_str)

    def get_nats_url(self) -> str:
        """Get NATS connection URL."""
        return os.getenv("NATS_URL", "nats://nats:4222")

    def get_grpc_port(self) -> int:
        """Get gRPC server port."""
        port_str = os.getenv("GRPC_PORT", "50054")
        return int(port_str)

