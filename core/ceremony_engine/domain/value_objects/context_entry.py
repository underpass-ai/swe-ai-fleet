"""ContextEntry: Immutable entry for execution context."""

from dataclasses import dataclass

from core.ceremony_engine.domain.value_objects.context_key import ContextKey


@dataclass(frozen=True)
class ContextEntry:
    """
    Value Object: Single entry in ExecutionContext.

    Domain Invariants:
    - key must be ContextKey
    """

    key: ContextKey
    value: object

    def __post_init__(self) -> None:
        if not isinstance(self.key, ContextKey):
            raise ValueError(f"ContextEntry key must be ContextKey, got {type(self.key)}")
