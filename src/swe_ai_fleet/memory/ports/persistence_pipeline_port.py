from __future__ import annotations

from typing import Any, Protocol


class PersistencePipelinePort(Protocol):
    def set(self, key: str, value: str, ex: int | None = None) -> Any: ...  # noqa: B032
    def lpush(self, key: str, value: str) -> Any: ...
    def expire(self, key: str, seconds: int) -> Any: ...
    def execute(self) -> list[Any]: ...