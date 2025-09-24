from __future__ import annotations

from typing import Any, Protocol

from swe_ai_fleet.memory.dtos.llm_call_dto import LlmCallDTO
from swe_ai_fleet.memory.dtos.llm_response_dto import LlmResponseDTO


class PersistenceStorePort(Protocol):
    """Protocol for RedisStore"""

    def save_llm_call(self, dto: LlmCallDTO) -> str: ...  # noqa: B032

    def save_llm_response(self, dto: LlmResponseDTO) -> str: ...

    def get_recent_events(
        self,
        session_id: str,
        count: int = 100,
    ) -> list[dict[str, Any]]: ...

    def get_context_window(
        self,
        session_id: str,
        max_chars: int = 12000,
    ) -> str: ...
