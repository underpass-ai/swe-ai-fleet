# src/swe_ai_fleet/context/adapters/neo4j_command_store.py
from __future__ import annotations
import os, time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, TransientError
from swe_ai_fleet.context.ports.graph_command_port import GraphCommandPort

@dataclass(frozen=True)
class Neo4jConfig:
    uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user: str = os.getenv("NEO4J_USER", "neo4j")
    password: str = os.getenv("NEO4J_PASSWORD", "test")
    database: Optional[str] = os.getenv("NEO4J_DATABASE") or None
    max_retries: int = int(os.getenv("NEO4J_MAX_RETRIES", "3"))
    base_backoff_s: float = float(os.getenv("NEO4J_BACKOFF", "0.25"))

class Neo4jCommandStore(GraphCommandPort):
    def __init__(self, cfg: Optional[Neo4jConfig] = None, driver: Optional[Driver] = None) -> None:
        self.cfg = cfg or Neo4jConfig()
        self.driver = driver or GraphDatabase.driver(self.cfg.uri, auth=(self.cfg.user, self.cfg.password))

    def close(self): self.driver.close()

    def _session(self) -> Session:
        if self.cfg.database:
            return self.driver.session(database=self.cfg.database)
        return self.driver.session()

    def _retry_write(self, fn, *a, **k):
        attempt = 0
        while True:
            try:
                return fn(*a, **k)
            except (ServiceUnavailable, TransientError):
                if attempt >= self.cfg.max_retries:
                    raise
                time.sleep(self.cfg.base_backoff_s * (2 ** attempt))
                attempt += 1

    def init_constraints(self, labels: Sequence[str]) -> None:
        cyphers = [f"CREATE CONSTRAINT IF NOT EXISTS FOR (n:{l}) REQUIRE n.id IS UNIQUE" for l in labels]
        def _tx(tx):
            for c in cyphers: tx.run(c)
        with self._session() as s:
            self._retry_write(s.execute_write, _tx)

    def upsert_entity(self, label: str, id: str, properties: Optional[Mapping[str, Any]] = None) -> None:
        props = dict(properties or {}); props["id"] = id
        cypher = f"MERGE (n:{label} {{id:$id}}) SET n += $props"
        with self._session() as s:
            self._retry_write(s.execute_write, lambda tx: tx.run(cypher, id=id, props=props))

    def upsert_entity_multi(self, labels: Iterable[str], id: str, properties: Optional[Mapping[str, Any]] = None) -> None:
        ls = list(labels)
        if not ls: raise ValueError("labels must be non-empty")
        label_expr = ":" + ":".join(sorted(set(ls)))
        props = dict(properties or {}); props["id"] = id
        cypher = f"MERGE (n{label_expr} {{id:$id}}) SET n += $props"
        with self._session() as s:
            self._retry_write(s.execute_write, lambda tx: tx.run(cypher, id=id, props=props))

    def relate(self, src_id: str, rel_type: str, dst_id: str, *,
               src_labels: Optional[Iterable[str]] = None,
               dst_labels: Optional[Iterable[str]] = None,
               properties: Optional[Mapping[str, Any]] = None) -> None:
        src_lbl = ":" + ":".join(sorted(set(src_labels))) if src_labels else ""
        dst_lbl = ":" + ":".join(sorted(set(dst_labels))) if dst_labels else ""
        cypher = (
            f"MATCH (a{src_lbl} {{id:$src}}), (b{dst_lbl} {{id:$dst}}) "
            f"MERGE (a)-[r:{rel_type}]->(b) SET r += $props"
        )
        with self._session() as s:
            self._retry_write(s.execute_write, lambda tx: tx.run(cypher, src=src_id, dst=dst_id, props=dict(properties or {})))
