"""AcceptanceCriteria aggregate value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple

from .acceptance_criterion import AcceptanceCriterion


@dataclass(frozen=True)
class AcceptanceCriteria:
    """Immutable collection of acceptance criteria."""

    values: Tuple[AcceptanceCriterion, ...]

    def __post_init__(self) -> None:
        if not self.values:
            raise ValueError("AcceptanceCriteria cannot be empty")

    @classmethod
    def from_iterable(cls, items: Iterable[str]) -> "AcceptanceCriteria":
        criteria = tuple(AcceptanceCriterion(item) for item in items)
        return cls(criteria)

    def __iter__(self):
        return iter(self.values)

    def __len__(self) -> int:
        return len(self.values)

