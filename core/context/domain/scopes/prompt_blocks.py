from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptBlocks:
    """Minimal prompt structure used by agents.

    - system: System instructions for the role.
    - context: Redacted, compact context block.
    - tools: Optional hint about tool usage.
    """

    system: str
    context: str
    tools: str
