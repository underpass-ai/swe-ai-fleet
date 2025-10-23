from dataclasses import dataclass


@dataclass(frozen=True)
class DecisionEdges:
    src_id: str
    rel_type: str
    dst_id: str
