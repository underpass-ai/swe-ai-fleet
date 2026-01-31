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

    def get_planning_ceremony_processor_url(self) -> str | None:
        """Get Planning Ceremony Processor gRPC URL (optional).

        When set, can be used to start ceremony-engine ceremonies (e.g. for
        future RPCs). Backlog Review does NOT use this; it is a Planning-domain
        flow (Ray, deliberations) and is decoupled from the ceremony processor.
        """
        ...

    def get_context_service_url(self) -> str:
        """Get Context Service gRPC URL.

        Returns:
            Context Service gRPC address (e.g., "context-service:50054")
        """
        ...

