from dataclasses import dataclass


@dataclass(frozen=True)
class RoleConfig:
    name: str
    replicas: int
    model_profile: str
