from typing import Any

from .architect import ArchitectSelector
from .config import SystemConfig
from .council import PeerCouncil


class Router:
    def __init__(
        self, config: SystemConfig, councils: dict[str, PeerCouncil], architect: ArchitectSelector
    ) -> None:
        self._config = config
        self._councils = councils
        self._architect = architect

    def dispatch(self, role: str, task: str, constraints: dict[str, Any]) -> dict[str, Any]:
        council = self._councils[role]
        ranked = council.deliberate(task, constraints)
        return self._architect.choose(ranked, constraints.get("architect_rubric", {}))
