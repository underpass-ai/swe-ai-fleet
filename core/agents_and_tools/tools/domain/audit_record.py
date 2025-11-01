"""Audit record entity for tool operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AuditRecord:
    """
    Immutable entity representing an audit record for tool operations.
    
    Following DDD principles:
    - Immutable (frozen=True)
    - Fail-fast validation in __post_init__
    - Self-contained business logic
    """

    tool: str
    operation: str
    params: dict[str, Any]
    success: bool
    metadata: dict[str, Any]
    workspace: str

    def __post_init__(self) -> None:
        """
        Validate entity invariants (fail-fast).
        
        Raises:
            ValueError: If any invariant is violated
        """
        if not self.tool or not self.tool.strip():
            raise ValueError("tool is required and cannot be empty (fail-fast)")
        
        if not self.operation or not self.operation.strip():
            raise ValueError("operation is required and cannot be empty (fail-fast)")
        
        if self.params is None:
            raise ValueError("params is required (use empty dict if no params) (fail-fast)")
        
        if not isinstance(self.success, bool):
            raise ValueError("success must be a boolean (fail-fast)")
        
        if self.metadata is None:
            raise ValueError("metadata is required (use empty dict if no metadata) (fail-fast)")
        
        if not self.workspace or not self.workspace.strip():
            raise ValueError("workspace is required and cannot be empty (fail-fast)")

    def to_dict(self) -> dict[str, Any]:
        """
        Convert audit record to dictionary for logging/storage.
        
        Note: This method is allowed in infrastructure layer entities
        that need serialization for audit trails.
        
        Returns:
            Dictionary representation of the audit record
        """
        return {
            "tool": self.tool,
            "operation": self.operation,
            "params": self.params,
            "success": self.success,
            "metadata": self.metadata,
            "workspace": self.workspace,
        }

    def is_successful(self) -> bool:
        """
        Check if the audited operation was successful.
        
        Returns:
            True if operation succeeded, False otherwise
        """
        return self.success

    def get_identifier(self) -> str:
        """
        Get a unique identifier for this audit record.
        
        Returns:
            String combining tool and operation
        """
        return f"{self.tool}.{self.operation}"

