"""Guard: Value Object representing a guard condition."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.ceremony_engine.domain.value_objects.context_key import ContextKey
from core.ceremony_engine.domain.value_objects.execution_context import ExecutionContext
from core.ceremony_engine.domain.value_objects.guard_name import GuardName
from core.ceremony_engine.domain.value_objects.guard_type import GuardType
from core.ceremony_engine.domain.value_objects.step_id import StepId

if TYPE_CHECKING:
    from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance


@dataclass(frozen=True)
class Guard:
    """
    Value Object: Guard condition.

    Domain Invariants:
    - name must be non-empty
    - type must be AUTOMATED or HUMAN
    - check must be non-empty for AUTOMATED guards
    - role is optional but recommended for HUMAN guards
    - threshold is optional (for numeric guards)
    - Immutable (frozen=True)

    Business Rules:
    - Guards define conditions that must be satisfied for transitions
    - AUTOMATED guards are evaluated programmatically
    - HUMAN guards require human decision/approval
    """

    name: GuardName
    type: GuardType
    check: str  # Expression/description
    role: str | None = None
    threshold: float | None = None

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Raises:
            ValueError: If guard is invalid
        """
        if not isinstance(self.name, GuardName):
            raise ValueError(f"Guard name must be GuardName, got {type(self.name)}")

        if not self.check or not self.check.strip():
            raise ValueError("Guard check cannot be empty")

        if self.type == GuardType.AUTOMATED and not self.check.strip():
            # check is required for automated guards (already validated above, but explicit)
            pass

    def evaluate(self, instance: "CeremonyInstance", context: ExecutionContext) -> bool:
        """Evaluate this guard against an instance and context.

        Args:
            instance: Ceremony instance (domain state access)
            context: Execution context (human approvals, thresholds, etc.)

        Returns:
            True if guard passes, False otherwise

        Raises:
            ValueError: If guard type is unknown
        """
        if self.type == GuardType.AUTOMATED:
            return self._evaluate_automated(instance)
        if self.type == GuardType.HUMAN:
            return self._evaluate_human(context)
        raise ValueError(f"Unknown guard type: {self.type}")

    def _evaluate_automated(self, instance: "CeremonyInstance") -> bool:
        """Evaluate an automated guard condition."""
        check = self.check.strip().lower()

        if check == "all_steps_completed":
            return instance.is_completed()

        if check.startswith("step_status:"):
            parts = check.split(":")
            if len(parts) == 3:
                step_id = StepId(parts[1])
                expected_status = parts[2].upper()
                try:
                    status = instance.get_step_status(step_id)
                    return status.value == expected_status
                except ValueError:
                    return False

        if check.startswith("threshold:") and self.threshold is not None:
            return True

        raise ValueError(f"Unsupported guard check: {self.check}")

    def _evaluate_human(self, context: ExecutionContext) -> bool:
        """Evaluate a human guard (check for approval)."""
        approvals = context.get_mapping(ContextKey.HUMAN_APPROVALS)
        if approvals is None:
            return False
        return bool(approvals.get(self.name.value, False))
