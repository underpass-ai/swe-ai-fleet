"""Neo4j connection configuration for Ceremony Engine."""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Neo4jConfig:
    """Neo4j connection configuration for Ceremony Engine.

    Domain Value Object:
    - Immutable configuration
    - Fail-fast validation
    - Environment variable defaults
    """

    uri: str = field(
        default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687")
    )
    user: str = field(default_factory=lambda: os.getenv("NEO4J_USER", "neo4j"))
    password: str = field(
        default_factory=lambda: os.getenv("NEO4J_PASSWORD", "password")
    )
    database: str | None = field(
        default_factory=lambda: os.getenv("NEO4J_DATABASE") or None
    )
    max_retries: int = 3
    base_backoff_s: float = 0.25
