from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LlmResponseDTO:
    """Class representing a LlmResponseDTO"""

    session_id: str
    task_id: str
    responder: str  # e.g., "agent:dev-1" or "model:qwen3-coder"
    model: str
    content: str
    usage: dict[str, int]  # tokens, latency_ms, etc.
    parent_msg_id: str | None = None

