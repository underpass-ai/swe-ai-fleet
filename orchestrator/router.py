from typing import Any, Dict, List
from .config import SystemConfig
from .council import PeerCouncil
from .architect import ArchitectSelector

class Router:
    def __init__(self, config: SystemConfig, councils: Dict[str, PeerCouncil],
                 architect: ArchitectSelector) -> None:
        self._config = config
        self._councils = councils
        self._architect = architect

    def dispatch(self, role: str, task: str, constraints: Dict[str, Any]) -> Dict[str, Any]:
        council = self._councils[role]
        ranked = council.deliberate(task, constraints)
        return self._architect.choose(ranked, constraints.get("architect_rubric", {}))
