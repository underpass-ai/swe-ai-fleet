from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LlmCallDTO:
    """Class representing a LlmCallDTO"""

    session_id: str
    task_id: str
    requester: str  # e.g., "user:123" or "agent:devops-1"
    model: str
    params: dict[str, Any]  # temperature, top_p, stop, seed, etc.
    content: str  # prompt
    parent_msg_id: str | None = None