"""ExecutionContext: Immutable context for ceremony execution."""

from collections.abc import Mapping
from dataclasses import dataclass

from core.ceremony_engine.domain.value_objects.context_entry import ContextEntry
from core.ceremony_engine.domain.value_objects.context_key import ContextKey


@dataclass(frozen=True)
class ExecutionContext:
    """
    Value Object: Execution context container.

    Domain Invariants:
    - entries must contain ContextEntry
    - keys must be unique
    """

    entries: tuple[ContextEntry, ...]

    def __post_init__(self) -> None:
        seen: set[ContextKey] = set()
        for entry in self.entries:
            if not isinstance(entry, ContextEntry):
                raise ValueError(
                    f"ExecutionContext entries must contain ContextEntry, got {type(entry)}"
                )
            if entry.key in seen:
                raise ValueError(f"Duplicate context key: {entry.key}")
            seen.add(entry.key)

    @staticmethod
    def empty() -> "ExecutionContext":
        """Create an empty ExecutionContext."""
        return ExecutionContext(entries=())

    @staticmethod
    def builder() -> "ExecutionContextBuilder":
        """Create a builder for ExecutionContext."""
        return ExecutionContextBuilder(entries=())

    def get(self, key: ContextKey, default: object | None = None) -> object | None:
        """Get a value for a given context key."""
        for entry in self.entries:
            if entry.key == key:
                return entry.value
        return default

    def get_mapping(self, key: ContextKey) -> Mapping[str, object] | None:
        """Get a mapping value for a context key if present."""
        value = self.get(key)
        if isinstance(value, Mapping):
            return value
        return None


@dataclass(frozen=True)
class ExecutionContextBuilder:
    """Builder for ExecutionContext."""

    entries: tuple[ContextEntry, ...]

    def with_entry(self, key: ContextKey, value: object) -> "ExecutionContextBuilder":
        """Return a new builder with the provided entry appended."""
        entry = ContextEntry(key=key, value=value)
        return ExecutionContextBuilder(entries=(*self.entries, entry))

    def build(self) -> ExecutionContext:
        """Build an ExecutionContext from current entries."""
        return ExecutionContext(entries=self.entries)
