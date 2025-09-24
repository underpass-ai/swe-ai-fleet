from __future__ import annotations

from typing import Any, Protocol

from swe_ai_fleet.memory.ports.persistence_pipeline_port import PersistencePipelinePort


class PersistenceKvPort(Protocol):
    def get(self, key: str) -> str | None: ...
    def xrevrange(self, key: str, count: int | None = None) -> list[tuple[str, dict[str, Any]]]: ...
    def pipeline(self) -> PersistencePipelinePort: ...