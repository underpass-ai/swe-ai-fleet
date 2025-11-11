"""RoleType enum for standard agent/user roles."""

from enum import Enum


class RoleType(str, Enum):
    """Enumeration of standard roles in the system.
    
    Following DDD:
    - Enum for fixed set of values
    - Type-safe role identifiers
    - NO magic strings
    
    Roles:
    - DEVELOPER: Software developer implementing features
    - ARCHITECT: Technical architect reviewing designs
    - QA: Quality assurance testing
    - PO: Product owner approving stories
    - SYSTEM: System-level operations (task derivation, automation)
    """
    
    DEVELOPER = "DEV"
    ARCHITECT = "ARCHITECT"
    QA = "QA"
    PRODUCT_OWNER = "PO"
    SYSTEM = "SYSTEM"
    
    def __str__(self) -> str:
        """String representation.
        
        Returns:
            Role value
        """
        return self.value

