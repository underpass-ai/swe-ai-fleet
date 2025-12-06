"""PlanApproval - Value Object for PO plan approval context.

Domain Layer (Value Object):
- Encapsulates PO's approval decision with semantic context
- WHY the PO approved (required for traceability)
- Concerns and priority adjustments (optional)
- Immutable record of approval decision
"""

from dataclasses import dataclass

from planning.domain.value_objects.actors.user_name import UserName


@dataclass(frozen=True)
class PlanApproval:
    """
    Value object representing a PO's approval of a plan preliminary.

    This captures the semantic context of the approval decision:
    - WHO approved (approved_by)
    - WHY they approved (po_notes) - REQUIRED for traceability
    - Any concerns to monitor (po_concerns) - optional
    - Priority adjustments with rationale (optional)

    Following DDD:
    - Immutable value object (@dataclass(frozen=True))
    - Rich validation in __post_init__
    - Business rules enforced at construction
    - Self-documenting domain concept

    Semantic Traceability:
    - PO notes explain WHY plan was approved (decision rationale)
    - This enables future agents/humans to understand the approval context
    - Supports accountability and auditability
    """

    approved_by: UserName
    po_notes: str
    po_concerns: str | None = None
    priority_adjustment: str | None = None
    po_priority_reason: str | None = None

    def __post_init__(self) -> None:
        """Validate approval business rules.

        Validation rules:
        1. po_notes is required and non-empty (WHY approved - semantic traceability)
        2. If priority_adjustment provided, po_priority_reason is required
        3. priority_adjustment must be valid value if provided (HIGH, MEDIUM, LOW)
        """
        # Rule 1: PO notes required for traceability
        if not self.po_notes or not self.po_notes.strip():
            raise ValueError(
                "po_notes is required: PO must explain WHY they approve the plan "
                "(required for semantic traceability and accountability)"
            )

        # Rule 2: Priority adjustment requires rationale
        if self.priority_adjustment and not self.po_priority_reason:
            raise ValueError(
                "po_priority_reason is required when priority_adjustment is provided: "
                "PO must explain WHY they adjust priority (semantic traceability)"
            )

        # Rule 3: Validate priority adjustment values
        if self.priority_adjustment:
            valid_priorities = {"HIGH", "MEDIUM", "LOW"}
            priority_upper = self.priority_adjustment.strip().upper()
            if priority_upper not in valid_priorities:
                raise ValueError(
                    f"Invalid priority_adjustment: '{self.priority_adjustment}'. "
                    f"Must be one of: {', '.join(sorted(valid_priorities))}"
                )

    @property
    def has_priority_adjustment(self) -> bool:
        """Check if PO adjusted priority from plan preliminary.

        Returns:
            True if priority was adjusted, False otherwise
        """
        return self.priority_adjustment is not None

    @property
    def has_concerns(self) -> bool:
        """Check if PO has concerns to monitor during execution.

        Returns:
            True if concerns were noted, False otherwise
        """
        return self.po_concerns is not None and bool(self.po_concerns.strip())

    @property
    def normalized_priority(self) -> str | None:
        """Get normalized priority adjustment (uppercase).

        Returns:
            Normalized priority (HIGH, MEDIUM, LOW) or None if no adjustment
        """
        if not self.priority_adjustment:
            return None
        return self.priority_adjustment.strip().upper()

    def format_for_audit_log(self) -> str:
        """Format approval for audit logging.

        Returns:
            Human-readable approval summary
        """
        parts = [f"Approved by: {self.approved_by.value}"]
        parts.append(f"Notes: {self.po_notes}")

        if self.has_concerns:
            parts.append(f"Concerns: {self.po_concerns}")

        if self.has_priority_adjustment:
            parts.append(
                f"Priority adjusted to {self.normalized_priority}: "
                f"{self.po_priority_reason}"
            )

        return " | ".join(parts)
