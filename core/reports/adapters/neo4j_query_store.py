from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

try:
    from neo4j import GraphDatabase
    from neo4j.exceptions import ServiceUnavailable, TransientError
except ImportError:
    GraphDatabase = None  # type: ignore[assignment]
    ServiceUnavailable = Exception  # type: ignore[assignment]
    TransientError = Exception  # type: ignore[assignment]


@dataclass(frozen=True)
class Neo4jConfig:
    uri: str = field(default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    user: str = field(default_factory=lambda: os.getenv("NEO4J_USER", "neo4j"))
    password: str = field(default_factory=lambda: os.getenv("NEO4J_PASSWORD", "test"))
    database: str | None = field(default_factory=lambda: os.getenv("NEO4J_DATABASE") or None)
    max_retries: int = field(default_factory=lambda: int(os.getenv("NEO4J_MAX_RETRIES", "3")))
    base_backoff_s: float = field(default_factory=lambda: float(os.getenv("NEO4J_BACKOFF", "0.25")))


class Neo4jQueryStore:
    """Minimal query store for the Reports bounded context."""

    def __init__(self, config: Neo4jConfig | None = None) -> None:
        self._config = config or Neo4jConfig()
        if GraphDatabase is None:
            raise ImportError("Neo4j driver not available")
        self._driver = GraphDatabase.driver(self._config.uri, auth=(self._config.user, self._config.password))

    def close(self) -> None:
        self._driver.close()

    def _session(self):
        return self._driver.session(database=self._config.database)

    def query(self, cypher: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        params = params or {}
        for attempt in range(self._config.max_retries):
            try:
                with self._session() as session:
                    result = session.run(cypher, params)
                    return [dict(record) for record in result]
            except (ServiceUnavailable, TransientError):
                if attempt == self._config.max_retries - 1:
                    raise
                import time as _t

                _t.sleep(self._config.base_backoff_s * (2**attempt))
        return []


