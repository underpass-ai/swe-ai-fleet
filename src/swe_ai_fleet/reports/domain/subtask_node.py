from dataclasses import dataclass


@dataclass(frozen=True)
class SubtaskNode:
    id: str
    title: str
    role: str
