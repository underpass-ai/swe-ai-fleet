from dataclasses import dataclass


@dataclass(frozen=True)
class RoleConfig:
    name: str
    replicas: int
    model_profile: str


@dataclass(frozen=True)
class SystemConfig:
    roles: list[RoleConfig]
    require_human_approval: bool = True
