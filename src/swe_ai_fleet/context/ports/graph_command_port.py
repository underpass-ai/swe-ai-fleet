# src/swe_ai_fleet/context/ports/graph_command_port.py
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Protocol


class GraphCommandPort(Protocol):
    def init_constraints(self, labels: Sequence[str]) -> None: ...
    def upsert_entity(self, label: str, id: str, properties: Mapping[str, Any] | None = None) -> None: ...
    def upsert_entity_multi(self, labels: Iterable[str], id: str, 
                           properties: Mapping[str, Any] | None = None) -> None: ...
    def relate(self, src_id: str, rel_type: str, dst_id: str, *,
               src_labels: Iterable[str] | None=None,
               dst_labels: Iterable[str] | None=None,
               properties: Mapping[str, Any] | None=None) -> None: ...
