from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RehydrationBundle:
    case_id: str
    generated_at_ms: int
    packs: dict[str, Any]  # role -> pack
    stats: dict[str, Any]
