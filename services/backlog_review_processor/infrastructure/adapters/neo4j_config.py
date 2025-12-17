"""Neo4j configuration for Backlog Review Processor Service."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Neo4jConfig:
    """Neo4j connection configuration."""

    uri: str
    user: str
    password: str
    database: str = "neo4j"

    @classmethod
    def from_env(cls) -> "Neo4jConfig":
        """Create config from environment variables.

        Returns:
            Neo4jConfig instance

        Raises:
            ValueError: If required env vars are missing
        """
        uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "")
        database = os.getenv("NEO4J_DATABASE", "neo4j")

        if not password:
            raise ValueError("NEO4J_PASSWORD environment variable is required")

        return cls(uri=uri, user=user, password=password, database=database)
