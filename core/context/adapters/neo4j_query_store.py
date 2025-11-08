# core/context/adapters/neo4j_query_store.py
"""Neo4j query store adapter - Infrastructure layer.

Implements GraphQueryPort using Neo4j driver.
Configuration is injected, NOT loaded from environment here (Dependency Inversion).
"""

from __future__ import annotations

import time
from typing import Any

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, TransientError

from core.context.domain.neo4j_config import Neo4jConfig
from core.context.domain.neo4j_queries import Neo4jQuery
from core.context.ports.graph_query_port import GraphQueryPort


class Neo4jQueryStore(GraphQueryPort):
    """Neo4j implementation of GraphQueryPort for read operations.

    This adapter receives configuration via dependency injection.
    All queries are defined in Neo4jQuery enum for centralization and testability.

    Follows fail-fast principle: if Neo4j is not available, import fails immediately.
    """

    def __init__(self, config: Neo4jConfig) -> None:
        """Initialize Neo4j query store with injected configuration.

        Args:
            config: Neo4jConfig domain value object (REQUIRED, no defaults)

        Raises:
            ValueError: If config is invalid
        """
        self._config = config
        self._driver = GraphDatabase.driver(
            self._config.uri,
            auth=(self._config.user, self._config.password)
        )

    def close(self) -> None:
        """Close the Neo4j driver connection."""
        self._driver.close()

    def _session(self):
        """Get a Neo4j session.

        Returns:
            Neo4j session with configured database
        """
        if self._config.database:
            return self._driver.session(database=self._config.database)
        return self._driver.session()

    def query(self, cypher: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute a Cypher query and return results.

        Implements exponential backoff retry for transient errors.

        Args:
            cypher: Cypher query string
            params: Query parameters

        Returns:
            List of result records as dictionaries

        Raises:
            ServiceUnavailable: If Neo4j is not available after retries
            TransientError: If transient error persists after retries
        """
        params = params or {}

        for attempt in range(self._config.max_retries):
            try:
                with self._session() as session:
                    result = session.run(cypher, params)
                    return [dict(record) for record in result]
            except (ServiceUnavailable, TransientError):
                if attempt == self._config.max_retries - 1:
                    raise  # Re-raise on last attempt (fail fast)
                # Exponential backoff
                time.sleep(self._config.base_backoff_s * (2**attempt))

        return []

    def case_plan(self, case_id: str) -> list[dict[str, Any]]:
        """Get plan information for a Story (formerly case).

        Note: Method name kept as case_plan for backward compatibility.
        Parameter name kept as case_id for backward compatibility.

        Args:
            case_id: Story identifier (legacy parameter name)

        Returns:
            List of plan records
        """
        return self.query(str(Neo4jQuery.GET_PLAN_FOR_STORY), {"story_id": case_id})

    def node_with_neighbors(self, node_id: str, depth: int = 1) -> list[dict[str, Any]]:
        """Get a node and its neighbors up to specified depth.

        Uses parameterized query from Neo4jQuery enum.

        Args:
            node_id: Node identifier
            depth: Traversal depth (default: 1)

        Returns:
            Node and its neighbors
        """
        # Build query with dynamic depth (depth must be known at query construction time)
        # This is a limitation of Cypher - relationship depth cannot be parameterized
        cypher = f"""
        MATCH (n {{id: $node_id}})-[r*1..{depth}]-(neighbor)
        RETURN n, collect(DISTINCT neighbor) AS neighbors, collect(DISTINCT r) AS relationships
        """
        return self.query(cypher, {"node_id": node_id})
