"""Neo4j configuration loader - Infrastructure layer.

Loads configuration from environment variables and constructs Neo4jConfig domain object.
"""

import os

from core.context.domain.neo4j_config import Neo4jConfig


class Neo4jConfigLoader:
    """Loader for Neo4j configuration from environment variables."""

    @staticmethod
    def load_from_env() -> Neo4jConfig:
        """Load Neo4j configuration from environment variables.

        Environment variables:
            NEO4J_URI: Connection URI (default: bolt://localhost:7687)
            NEO4J_USER: Username (default: neo4j)
            NEO4J_PASSWORD: Password (required, no default)
            NEO4J_DATABASE: Database name (default: neo4j)
            NEO4J_MAX_RETRIES: Max retry attempts (default: 3)
            NEO4J_BACKOFF: Base backoff in seconds (default: 0.25)

        Returns:
            Neo4jConfig domain value object

        Raises:
            ValueError: If required environment variables are missing or invalid
        """
        password = os.getenv("NEO4J_PASSWORD")
        if not password:
            raise ValueError("NEO4J_PASSWORD environment variable is required")

        return Neo4jConfig(
            uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=password,
            database=os.getenv("NEO4J_DATABASE", "neo4j"),
            max_retries=int(os.getenv("NEO4J_MAX_RETRIES", "3")),
            base_backoff_s=float(os.getenv("NEO4J_BACKOFF", "0.25")),
        )

    @staticmethod
    def from_dict(config: dict[str, str | int | float]) -> Neo4jConfig:
        """Load Neo4j configuration from dictionary.

        Useful for testing with mock configurations.

        Args:
            config: Dictionary with configuration keys

        Returns:
            Neo4jConfig domain value object
        """
        return Neo4jConfig(
            uri=str(config["uri"]),
            user=str(config["user"]),
            password=str(config["password"]),
            database=str(config.get("database", "neo4j")),
            max_retries=int(config.get("max_retries", 3)),
            base_backoff_s=float(config.get("base_backoff_s", 0.25)),
        )

