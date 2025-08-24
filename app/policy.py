import yaml
from pathlib import Path
from typing import Any, Dict, List

CONFIG_PATH = Path("/workspace/config/scopes.yaml")


class PromptScopePolicy:
    def __init__(self, config_path: Path = CONFIG_PATH) -> None:
        self.config_path = config_path
        self.config: Dict[str, Any] = {"roles": {}}
        self.reload()

    def reload(self) -> None:
        if self.config_path.exists():
            with self.config_path.open("r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f) or {"roles": {}}
        else:
            self.config = {"roles": {}}

    def is_tool_allowed(self, role: str, tool_name: str) -> bool:
        role_cfg = (self.config.get("roles") or {}).get(role) or {}
        tools: List[str] = role_cfg.get("allowed_tools") or []
        return tool_name in tools

    def allowed_scopes(self, role: str) -> List[str]:
        role_cfg = (self.config.get("roles") or {}).get(role) or {}
        return list(role_cfg.get("scopes") or [])

    def filter_context(self, role: str, context: Dict[str, Any]) -> Dict[str, Any]:
        scopes = set(self.allowed_scopes(role))
        filtered: Dict[str, Any] = {}
        if "chat" in scopes and context.get("chat"):
            filtered["chat"] = context["chat"]
        if "backlog" in scopes and context.get("backlog"):
            filtered["backlog"] = context["backlog"]
        if "graph" in scopes and context.get("graph"):
            filtered["graph"] = context["graph"]
        if "reports" in scopes and context.get("reports"):
            filtered["reports"] = context["reports"]
        return filtered