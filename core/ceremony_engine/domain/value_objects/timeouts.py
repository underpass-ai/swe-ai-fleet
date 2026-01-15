"""Timeouts: Value Object representing timeout configuration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Timeouts:
    """
    Value Object: Timeout configuration.

    Domain Invariants:
    - step_default must be > 0
    - step_max must be > 0
    - ceremony_max must be > 0
    - step_default must be <= step_max
    - Immutable (frozen=True)

    Business Rules:
    - Defines timeout limits for steps and ceremonies
    - step_default is used when step doesn't specify timeout_seconds
    - step_max is the maximum allowed timeout for any step
    - ceremony_max is the maximum total time for the entire ceremony
    """

    step_default: int  # seconds
    step_max: int  # seconds
    ceremony_max: int  # seconds

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Raises:
            ValueError: If timeouts are invalid
        """
        if self.step_default <= 0:
            raise ValueError(f"step_default must be > 0: {self.step_default}")

        if self.step_max <= 0:
            raise ValueError(f"step_max must be > 0: {self.step_max}")

        if self.ceremony_max <= 0:
            raise ValueError(f"ceremony_max must be > 0: {self.ceremony_max}")

        if self.step_default > self.step_max:
            raise ValueError(
                f"step_default ({self.step_default}) must be <= step_max ({self.step_max})"
            )
