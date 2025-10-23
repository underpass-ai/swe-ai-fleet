from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentConfig:
    sprint_id: str
    role: str
    workspace: str = "/workspace"
    pick_first_ready: bool = True  # naive heuristic for MVP