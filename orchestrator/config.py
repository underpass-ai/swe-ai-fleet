from dataclasses import dataclass
from typing import List

@dataclass(frozen=True)
class RoleConfig:
    name: str
    replicas: int
    model_profile: str

@dataclass(frozen=True)
class SystemConfig:
    roles: List[RoleConfig]
    require_human_approval: bool = True
