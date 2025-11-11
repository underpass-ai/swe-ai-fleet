"""Configuration port for Planning Service."""

from typing import Protocol


class ConfigurationPort(Protocol):
    """
    Port (interface) for loading service configuration.

    Infrastructure adapters will implement this by reading from:
    - Environment variables
    - Config files
    - Secret managers
    - etc.
    """

    def get_neo4j_uri(self) -> str:
        """Get Neo4j connection URI."""
        ...

    def get_neo4j_user(self) -> str:
        """Get Neo4j username."""
        ...

    def get_neo4j_password(self) -> str:
        """Get Neo4j password."""
        ...

    def get_neo4j_database(self) -> str | None:
        """Get Neo4j database name (optional)."""
        ...

    def get_valkey_host(self) -> str:
        """Get Valkey host."""
        ...

    def get_valkey_port(self) -> int:
        """Get Valkey port."""
        ...

    def get_valkey_db(self) -> int:
        """Get Valkey database number."""
        ...

    def get_nats_url(self) -> str:
        """Get NATS connection URL."""
        ...

    def get_grpc_port(self) -> int:
        """Get gRPC server port."""
        ...

    def get_task_derivation_config_path(self) -> str:
        """Get path to task derivation config file.

        Returns:
            Path to task_derivation.yaml
        """
        ...

