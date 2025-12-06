"""Review Approval Status value object."""

from dataclasses import dataclass
from enum import Enum


class ReviewApprovalStatusEnum(str, Enum):
    """
    Approval status for a Story Review Result.

    States:
    - PENDING: Review completed, awaiting PO approval
    - APPROVED: PO approved the plan
    - REJECTED: PO rejected the plan
    """

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class ReviewApprovalStatus:
    """
    Value Object: Approval status of a Story Review Result.

    Domain Invariants:
    - Status must be one of the valid ReviewApprovalStatusEnum values

    Immutability: frozen=True ensures no mutation after creation.
    """

    value: ReviewApprovalStatusEnum

    def __post_init__(self) -> None:
        """
        Fail-fast validation.

        Raises:
            ValueError: If status is not a valid ReviewApprovalStatusEnum.
        """
        if not isinstance(self.value, ReviewApprovalStatusEnum):
            raise ValueError(
                f"Invalid status: {self.value}. Must be ReviewApprovalStatusEnum."
            )

    def to_string(self) -> str:
        """
        Convert status to string representation.

        Returns:
            String representation of the status.
        """
        return self.value.value

    def is_pending(self) -> bool:
        """Check if status is PENDING."""
        return self.value == ReviewApprovalStatusEnum.PENDING

    def is_approved(self) -> bool:
        """Check if status is APPROVED."""
        return self.value == ReviewApprovalStatusEnum.APPROVED

    def is_rejected(self) -> bool:
        """Check if status is REJECTED."""
        return self.value == ReviewApprovalStatusEnum.REJECTED

    def __str__(self) -> str:
        """String representation for logging."""
        return self.value.value


