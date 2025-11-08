"""Neo4j configuration value object - Domain layer.

Configuration is defined in domain but loaded/injected from infrastructure.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Neo4jConfig:
    """Neo4j connection configuration.

    This is a pure domain value object. Infrastructure layer is responsible
    for loading these values from environment variables or config files.
    """

    uri: str
    user: str
    password: str
    database: str = "neo4j"
    max_retries: int = 3
    base_backoff_s: float = 0.25

    def __post_init__(self) -> None:
        """Validate configuration."""
        if not self.uri:
            raise ValueError("Neo4j URI cannot be empty")
        if not self.user:
            raise ValueError("Neo4j user cannot be empty")
        if not self.password:
            raise ValueError("Neo4j password cannot be empty")
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if self.base_backoff_s <= 0:
            raise ValueError("base_backoff_s must be > 0")

