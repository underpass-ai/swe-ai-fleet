# src/swe_ai_fleet/context/adapters/neo4j_query_store.py
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

try:
    from neo4j import GraphDatabase
    from neo4j.exceptions import ServiceUnavailable, TransientError
except ImportError:
    # Handle case where neo4j is not available (e.g., in tests with mocked neo4j)
    GraphDatabase = None
    ServiceUnavailable = Exception
    TransientError = Exception

from swe_ai_fleet.context.ports.graph_query_port import GraphQueryPort


@dataclass(frozen=True)
class Neo4jConfig:
    """Configuration for Neo4j connection."""
    
    uri: str = field(default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    user: str = field(default_factory=lambda: os.getenv("NEO4J_USER", "neo4j"))
    password: str = field(default_factory=lambda: os.getenv("NEO4J_PASSWORD", "test"))
    database: str | None = field(default_factory=lambda: os.getenv("NEO4J_DATABASE") or None)
    max_retries: int = field(default_factory=lambda: int(os.getenv("NEO4J_MAX_RETRIES", "3")))
    base_backoff_s: float = field(default_factory=lambda: float(os.getenv("NEO4J_BACKOFF", "0.25")))


class Neo4jQueryStore(GraphQueryPort):
    """Neo4j implementation of GraphQueryPort for read operations."""
    
    def __init__(self, config: Neo4jConfig | None = None) -> None:
        self._config = config or Neo4jConfig()
        if GraphDatabase is None:
            raise ImportError("Neo4j driver not available")
        self._driver = GraphDatabase.driver(
            self._config.uri,
            auth=(self._config.user, self._config.password)
        )
    
    def close(self) -> None:
        """Close the Neo4j driver connection."""
        self._driver.close()
    
    def _session(self):
        """Get a Neo4j session."""
        return self._driver.session(database=self._config.database)
    
    def query(self, cypher: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute a Cypher query and return results."""
        params = params or {}
        
        for attempt in range(self._config.max_retries):
            try:
                with self._session() as session:
                    result = session.run(cypher, params)
                    return [dict(record) for record in result]
            except (ServiceUnavailable, TransientError):
                if attempt == self._config.max_retries - 1:
                    raise
                # Exponential backoff
                import time
                time.sleep(self._config.base_backoff_s * (2 ** attempt))
        
        return []
    
    def case_plan(self, case_id: str) -> list[dict[str, Any]]:
        """Get plan information for a case."""
        cypher = """
        MATCH (c:Case {id: $case_id})-[:HAS_PLAN]->(p:PlanVersion)
        RETURN p.id as plan_id, p.version as version, p.case_id as case_id
        ORDER BY p.version DESC
        """
        return self.query(cypher, {"case_id": case_id})
    
    def node_with_neighbors(self, node_id: str, depth: int = 1) -> list[dict[str, Any]]:
        """Get a node and its neighbors up to specified depth."""
        cypher = f"""
        MATCH (n {{id: $node_id}})-[r*1..{depth}]-(neighbor)
        RETURN n, r, neighbor
        """
        return self.query(cypher, {"node_id": node_id})
