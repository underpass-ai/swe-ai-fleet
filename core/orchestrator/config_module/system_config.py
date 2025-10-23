from dataclasses import dataclass

from .role_config import RoleConfig


@dataclass(frozen=True)
class SystemConfig:
    roles: list[RoleConfig]
    require_human_approval: bool = True
