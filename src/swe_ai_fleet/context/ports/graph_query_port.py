# src/swe_ai_fleet/context/ports/graph_query_port.py
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


class GraphQueryPort(Protocol):
    def query(self, cypher: str, params: Mapping[str, Any] | None = None) -> list[dict[str, Any]]: ...
    # convenience reads
    def case_plan(self, case_id: str) -> list[dict[str, Any]]: ...
    def node_with_neighbors(self, node_id: str, depth: int = 1) -> list[dict[str, Any]]: ...
